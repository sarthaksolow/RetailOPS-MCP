"""
Persistent MCP Client and Session Pool for RetailOps.
Enables reusing long-lived MCP server processes across multiple workflow executions
to measure and isolate process lifecycle overhead vs. MCP IPC communication overhead.
"""
import os
import sys
import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import AsyncExitStack

from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession

# Ensure root dir is in path
ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "client") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "client"))

from client.telemetry import (
    ServiceCallTelemetry,
    ExecutionTelemetry,
    TelemetryLogger,
    now_iso
)


class PersistentMCPSessionPool:
    """
    Manages long-lived ClientSession instances and stdio subprocesses for all 4 MCP services.
    Supports starting all servers once, executing multiple workflows, measuring fine-grained
    lifecycle events, and cleanly closing all sessions and subprocesses.
    """

    def __init__(self, server_paths: Optional[Dict[str, Path]] = None):
        self.root_dir = ROOT_DIR
        self.server_paths = server_paths or {
            "enricher": Path(os.getenv(
                "RETAILOPS_ENRICHER_SERVER_PATH",
                str(self.root_dir / "servers" / "catalog-enricher" / "server.py")
            )),
            "forecasting": Path(os.getenv(
                "RETAILOPS_FORECASTING_SERVER_PATH",
                str(self.root_dir / "servers" / "forecasting" / "server.py")
            )),
            "replenishment": Path(os.getenv(
                "RETAILOPS_REPLENISHMENT_SERVER_PATH",
                str(self.root_dir / "servers" / "replenishment" / "server.py")
            )),
            "pricing": Path(os.getenv(
                "RETAILOPS_PRICING_SERVER_PATH",
                str(self.root_dir / "servers" / "pricing-strategy" / "server.py")
            ))
        }
        self.stack: Optional[AsyncExitStack] = None
        self.sessions: Dict[str, ClientSession] = {}
        self.is_connected: bool = False
        self.startup_timing: Dict[str, Dict[str, float]] = {}
        self.shutdown_timing_ms: float = 0.0

    async def start(self) -> Dict[str, Any]:
        """
        Start all 4 MCP server subprocesses and initialize client sessions.
        Directly measures spawn duration, session entrance, and handshake initialization.
        """
        if self.is_connected:
            return self.startup_timing

        self.stack = AsyncExitStack()
        self.sessions = {}
        self.startup_timing = {}

        t_total_start = time.perf_counter()

        for name, path in self.server_paths.items():
            t_spawn_start = time.perf_counter()
            params = StdioServerParameters(
                command=sys.executable,
                args=[str(path)],
                env={"OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", "")}
            )
            read, write = await self.stack.enter_async_context(stdio_client(params))
            t_spawn_end = time.perf_counter()

            t_sess_start = time.perf_counter()
            session = await self.stack.enter_async_context(ClientSession(read, write))
            t_sess_end = time.perf_counter()

            t_init_start = time.perf_counter()
            await session.initialize()
            t_init_end = time.perf_counter()

            self.sessions[name] = session
            self.startup_timing[name] = {
                "process_spawn_ms": round((t_spawn_end - t_spawn_start) * 1000, 2),
                "session_context_ms": round((t_sess_end - t_sess_start) * 1000, 2),
                "initialize_handshake_ms": round((t_init_end - t_init_start) * 1000, 2),
                "total_startup_ms": round((t_init_end - t_spawn_start) * 1000, 2)
            }

        t_total_end = time.perf_counter()
        self.is_connected = True
        self.startup_timing["_total_pool_startup_ms"] = round((t_total_end - t_total_start) * 1000, 2)
        return self.startup_timing

    async def close(self) -> float:
        """
        Cleanly terminate all sessions and subprocesses.
        Measures shutdown duration directly.
        """
        if not self.is_connected or not self.stack:
            return 0.0

        t_close_start = time.perf_counter()
        try:
            await self.stack.aclose()
        finally:
            self.sessions.clear()
            self.stack = None
            self.is_connected = False

        t_close_end = time.perf_counter()
        self.shutdown_timing_ms = round((t_close_end - t_close_start) * 1000, 2)
        return self.shutdown_timing_ms

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def call_tool_on_session(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool on an existing, persistent session."""
        if not self.is_connected or server_name not in self.sessions:
            raise RuntimeError(f"Session for server '{server_name}' is not running or connected.")

        session = self.sessions[server_name]
        response = await session.call_tool(tool_name, arguments)

        if hasattr(response, "content") and response.content:
            for c in response.content:
                if hasattr(c, "text"):
                    return json.loads(c.text)
        return {"error": f"No valid text content received from tool {tool_name}"}


class PersistentRetailOpsClient:
    """
    RetailOps Orchestrator Client using persistent, reusable MCP sessions.
    Executes the 4-stage pipeline (Enrichment -> Forecast -> Replenishment -> Pricing)
    over persistent stdio sessions without restarting subprocesses per call.
    """

    def __init__(
        self,
        pool: PersistentMCPSessionPool,
        telemetry_logger: Optional[TelemetryLogger] = None
    ):
        self.pool = pool
        self.telemetry_logger = telemetry_logger or TelemetryLogger()

    async def run_full_workflow(
        self,
        product_name: str,
        days_ahead: int = 30
    ) -> Dict[str, Any]:
        """
        Execute full workflow over persistent sessions.
        Maintains strict state isolation and schema parity with the standard client.
        """
        if not self.pool.is_connected:
            await self.pool.start()

        execution_id = f"exec-pers-{uuid.uuid4().hex[:12]}"
        workflow_name = "retail_operations_persistent_orchestrator"
        start_time_iso = now_iso()
        t_start_perf = time.perf_counter()

        completed_steps = []
        failed_steps = []
        service_calls = []
        errors = []
        workflow_status = "running"

        state: Dict[str, Any] = {
            "execution_id": execution_id,
            "product_name": product_name,
            "days_ahead": int(days_ahead),
            "category": "general",
            "brand": "Unknown",
            "description": "",
            "enrichment_narrative": "",
            "forecast_data": {},
            "base_forecast": 0.0,
            "final_forecast": 0.0,
            "seasonal_multiplier": 1.0,
            "event": "None",
            "forecast_narrative": "",
            "replenishment_data": {},
            "reorder_qty": 0,
            "reorder_timing": "unknown",
            "stockout_risk": "unknown",
            "replenishment_narrative": "",
            "pricing_data": {},
            "current_price": 0.0,
            "recommended_price": 0.0,
            "price_change_pct": 0.0,
            "recommendation_type": "maintain",
            "pricing_narrative": ""
        }

        # -------------------------------------------------------------
        # Stage 1: Catalog Enrichment
        # -------------------------------------------------------------
        t_s1_iso = now_iso()
        t_s1_start = time.perf_counter()
        try:
            enrich_result = await self.pool.call_tool_on_session(
                "enricher",
                "enrichProduct",
                {"input": {"product_name": product_name, "product_data": {}}}
            )
            t_s1_dur = round((time.perf_counter() - t_s1_start) * 1000, 2)

            if "error" in enrich_result:
                errors.append(f"Enrichment: {enrich_result['error']}")
                failed_steps.append("enrich")
                state["category"] = "general"
                service_calls.append(ServiceCallTelemetry(
                    service_name="Catalog Enricher",
                    tool_name="enrichProduct",
                    start_time=t_s1_iso,
                    end_time=now_iso(),
                    duration_ms=t_s1_dur,
                    status="failure",
                    error=enrich_result["error"]
                ).to_dict())
            else:
                completed_steps.append("enrich")
                state["category"] = enrich_result.get("category", "general")
                state["brand"] = enrich_result.get("brand", "Unknown")
                state["description"] = enrich_result.get("description", "")
                state["enrichment_narrative"] = enrich_result.get("narrative", "")
                service_calls.append(ServiceCallTelemetry(
                    service_name="Catalog Enricher",
                    tool_name="enrichProduct",
                    start_time=t_s1_iso,
                    end_time=now_iso(),
                    duration_ms=t_s1_dur,
                    status="success"
                ).to_dict())
        except Exception as e:
            t_s1_dur = round((time.perf_counter() - t_s1_start) * 1000, 2)
            errors.append(f"Enrichment: {e}")
            failed_steps.append("enrich")
            service_calls.append(ServiceCallTelemetry(
                service_name="Catalog Enricher",
                tool_name="enrichProduct",
                start_time=t_s1_iso,
                end_time=now_iso(),
                duration_ms=t_s1_dur,
                status="failure",
                error=str(e)
            ).to_dict())

        # -------------------------------------------------------------
        # Stage 2: Forecasting
        # -------------------------------------------------------------
        t_s2_iso = now_iso()
        t_s2_start = time.perf_counter()
        try:
            forecast_result = await self.pool.call_tool_on_session(
                "forecasting",
                "getForecast",
                {"category": state["category"], "days_ahead": state["days_ahead"]}
            )
            t_s2_dur = round((time.perf_counter() - t_s2_start) * 1000, 2)

            if "error" in forecast_result:
                errors.append(f"Forecasting: {forecast_result['error']}")
                failed_steps.append("forecast")
                workflow_status = "failed_forecast"
                service_calls.append(ServiceCallTelemetry(
                    service_name="Forecasting",
                    tool_name="getForecast",
                    start_time=t_s2_iso,
                    end_time=now_iso(),
                    duration_ms=t_s2_dur,
                    status="failure",
                    error=forecast_result["error"]
                ).to_dict())
            else:
                completed_steps.append("forecast")
                state["forecast_data"] = forecast_result
                state["base_forecast"] = forecast_result.get("base_forecast", 0.0)
                state["final_forecast"] = forecast_result.get("final_forecast", 0.0)
                state["seasonal_multiplier"] = forecast_result.get("seasonal_multiplier", 1.0)
                state["event"] = forecast_result.get("event", "None")
                state["forecast_narrative"] = forecast_result.get("narrative", "")
                service_calls.append(ServiceCallTelemetry(
                    service_name="Forecasting",
                    tool_name="getForecast",
                    start_time=t_s2_iso,
                    end_time=now_iso(),
                    duration_ms=t_s2_dur,
                    status="success"
                ).to_dict())
        except Exception as e:
            t_s2_dur = round((time.perf_counter() - t_s2_start) * 1000, 2)
            errors.append(f"Forecasting: {e}")
            failed_steps.append("forecast")
            workflow_status = "failed_forecast"
            service_calls.append(ServiceCallTelemetry(
                service_name="Forecasting",
                tool_name="getForecast",
                start_time=t_s2_iso,
                end_time=now_iso(),
                duration_ms=t_s2_dur,
                status="failure",
                error=str(e)
            ).to_dict())

        # -------------------------------------------------------------
        # Stage 3: Replenishment Decision
        # -------------------------------------------------------------
        if workflow_status != "failed_forecast":
            t_s3_iso = now_iso()
            t_s3_start = time.perf_counter()
            try:
                cat = state["category"]
                inventory_levels = {
                    "tv": {"current": 45, "in_transit": 10},
                    "laptop": {"current": 25, "in_transit": 5},
                    "phone": {"current": 80, "in_transit": 20},
                    "electronics": {"current": 150, "in_transit": 50},
                    "fashion": {"current": 350, "in_transit": 50},
                    "groceries": {"current": 800, "in_transit": 200},
                }
                inv = inventory_levels.get(cat, {"current": 200, "in_transit": 50})
                replenish_input = {
                    "category": cat,
                    "forecast": {
                        "forecasted_demand": state["forecast_data"].get("final_forecast"),
                        "avg_daily_demand": state["forecast_data"].get("final_forecast", 0) / 30,
                        "demand_volatility": "medium",
                        "event": {
                            "name": state["forecast_data"].get("event"),
                            "days_to_event": 10 if state["forecast_data"].get("event") else None
                        }
                    },
                    "inventory": {
                        "current_stock": inv["current"],
                        "in_transit_stock": inv["in_transit"]
                    },
                    "supplier": {
                        "lead_time_days": 10,
                        "minimum_order_quantity": 50
                    }
                }

                replenish_result = await self.pool.call_tool_on_session(
                    "replenishment",
                    "getReplenishmentDecision",
                    {"input": replenish_input}
                )
                t_s3_dur = round((time.perf_counter() - t_s3_start) * 1000, 2)

                if "error" in replenish_result:
                    errors.append(f"Replenishment: {replenish_result['error']}")
                    failed_steps.append("replenish")
                    workflow_status = "failed_replenishment"
                    service_calls.append(ServiceCallTelemetry(
                        service_name="Replenishment",
                        tool_name="getReplenishmentDecision",
                        start_time=t_s3_iso,
                        end_time=now_iso(),
                        duration_ms=t_s3_dur,
                        status="failure",
                        error=replenish_result["error"]
                    ).to_dict())
                else:
                    completed_steps.append("replenish")
                    state["replenishment_data"] = replenish_result
                    state["reorder_qty"] = replenish_result.get("reorder_qty", 0)
                    state["reorder_timing"] = replenish_result.get("reorder_timing", "unknown")
                    state["stockout_risk"] = replenish_result.get("stockout_risk", "unknown")
                    state["replenishment_narrative"] = replenish_result.get("narrative", "")
                    service_calls.append(ServiceCallTelemetry(
                        service_name="Replenishment",
                        tool_name="getReplenishmentDecision",
                        start_time=t_s3_iso,
                        end_time=now_iso(),
                        duration_ms=t_s3_dur,
                        status="success"
                    ).to_dict())
            except Exception as e:
                t_s3_dur = round((time.perf_counter() - t_s3_start) * 1000, 2)
                errors.append(f"Replenishment: {e}")
                failed_steps.append("replenish")
                workflow_status = "failed_replenishment"
                service_calls.append(ServiceCallTelemetry(
                    service_name="Replenishment",
                    tool_name="getReplenishmentDecision",
                    start_time=t_s3_iso,
                    end_time=now_iso(),
                    duration_ms=t_s3_dur,
                    status="failure",
                    error=str(e)
                ).to_dict())

        # -------------------------------------------------------------
        # Stage 4: Pricing Strategy
        # -------------------------------------------------------------
        if "failed" not in workflow_status:
            t_s4_iso = now_iso()
            t_s4_start = time.perf_counter()
            try:
                default_prices = {
                    "electronics": 9000.0,
                    "tv": 28000.0,
                    "laptop": 48000.0,
                    "phone": 16000.0,
                    "kitchen_appliances": 5500.0,
                    "fashion": 1500.0,
                    "groceries": 220.0
                }
                cur_price = default_prices.get(state["category"], 5000.0)

                pricing_result = await self.pool.call_tool_on_session(
                    "pricing",
                    "getPricingStrategy",
                    {
                        "input": {
                            "category": state["category"],
                            "current_price": cur_price,
                            "forecasted_demand": state["final_forecast"],
                            "inventory_level": 100,
                            "target_profit_pct": 0
                        }
                    }
                )
                t_s4_dur = round((time.perf_counter() - t_s4_start) * 1000, 2)

                if "error" in pricing_result:
                    errors.append(f"Pricing: {pricing_result['error']}")
                    failed_steps.append("price")
                    workflow_status = "failed_pricing"
                    service_calls.append(ServiceCallTelemetry(
                        service_name="Pricing Strategy",
                        tool_name="getPricingStrategy",
                        start_time=t_s4_iso,
                        end_time=now_iso(),
                        duration_ms=t_s4_dur,
                        status="failure",
                        error=pricing_result["error"]
                    ).to_dict())
                else:
                    completed_steps.append("price")
                    state["pricing_data"] = pricing_result
                    state["current_price"] = pricing_result.get("current_price", cur_price)
                    state["recommended_price"] = pricing_result.get("recommended_price", cur_price)
                    state["price_change_pct"] = pricing_result.get("price_change_pct", 0.0)
                    state["recommendation_type"] = pricing_result.get("recommendation_type", "maintain")
                    state["pricing_narrative"] = pricing_result.get("narrative", "")
                    service_calls.append(ServiceCallTelemetry(
                        service_name="Pricing Strategy",
                        tool_name="getPricingStrategy",
                        start_time=t_s4_iso,
                        end_time=now_iso(),
                        duration_ms=t_s4_dur,
                        status="success"
                    ).to_dict())
                    workflow_status = "completed"
            except Exception as e:
                t_s4_dur = round((time.perf_counter() - t_s4_start) * 1000, 2)
                errors.append(f"Pricing: {e}")
                failed_steps.append("price")
                workflow_status = "failed_pricing"
                service_calls.append(ServiceCallTelemetry(
                    service_name="Pricing Strategy",
                    tool_name="getPricingStrategy",
                    start_time=t_s4_iso,
                    end_time=now_iso(),
                    duration_ms=t_s4_dur,
                    status="failure",
                    error=str(e)
                ).to_dict())

        t_end_perf = time.perf_counter()
        end_time_iso = now_iso()
        total_duration_ms = round((t_end_perf - t_start_perf) * 1000, 2)

        result = {
            "execution_id": execution_id,
            "workflow_name": workflow_name,
            "start_time": start_time_iso,
            "end_time": end_time_iso,
            "total_duration_ms": total_duration_ms,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "service_calls": service_calls,
            "product_name": product_name,
            "category": state["category"],
            "timestamp": end_time_iso,
            "status": workflow_status,
            "enrichment": {
                "category": state["category"],
                "brand": state["brand"],
                "description": state["description"],
                "narrative": state["enrichment_narrative"]
            },
            "forecast": {
                "final": state["final_forecast"],
                "event": state["event"],
                "narrative": state["forecast_narrative"]
            },
            "replenishment": {
                "reorder_qty": state["reorder_qty"],
                "timing": state["reorder_timing"],
                "narrative": state["replenishment_narrative"]
            },
            "pricing": {
                "recommended_price": state["recommended_price"],
                "change_pct": state["price_change_pct"],
                "narrative": state["pricing_narrative"]
            },
            "errors": errors,
            "architecture": "persistent_mcp",
            "partial_result": {
                "category": state["category"],
                "enrichment": {
                    "category": state["category"],
                    "brand": state["brand"],
                    "description": state["description"],
                    "narrative": state["enrichment_narrative"]
                },
                "forecast": {
                    "final": state["final_forecast"],
                    "event": state["event"],
                    "narrative": state["forecast_narrative"]
                },
                "replenishment": {
                    "reorder_qty": state["reorder_qty"],
                    "timing": state["reorder_timing"],
                    "narrative": state["replenishment_narrative"]
                },
                "pricing": {
                    "recommended_price": state["recommended_price"],
                    "change_pct": state["price_change_pct"],
                    "narrative": state["pricing_narrative"]
                }
            }
        }

        # Log telemetry
        exec_telemetry = ExecutionTelemetry(
            execution_id=execution_id,
            workflow_name=workflow_name,
            product_name=product_name,
            category=state["category"],
            start_time=start_time_iso,
            end_time=end_time_iso,
            total_duration_ms=total_duration_ms,
            workflow_status=workflow_status,
            completed_steps=completed_steps,
            failed_steps=failed_steps,
            service_calls=service_calls,
            partial_result=result["partial_result"],
            errors=errors,
            architecture="persistent_mcp"
        )
        self.telemetry_logger.log_execution(exec_telemetry)
        return result
