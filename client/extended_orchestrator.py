"""
Extended RetailOps MCP Client - LangGraph Orchestrator (Task 08).
Chains 5 specialized MCP microservices:
Catalog Enricher -> Forecasting -> Replenishment -> Supplier Intelligence -> Pricing Strategy.

Preserves the existing 4-stage workflow and MCP servers completely untouched while
demonstrating modular extensibility in the MCP-based architecture.
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from typing import TypedDict, Annotated, Dict, Any, List, Optional
from datetime import datetime
import time
import uuid

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "client") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "client"))

from client.telemetry import ServiceCallTelemetry, ExecutionTelemetry, TelemetryLogger, now_iso
from client.orchestrator import MCPServerManager, RetailOpsState

load_dotenv()

def log(msg: str):
    print(f"[EXTENDED-CLIENT] {msg}", file=sys.stderr, flush=True)


class ExtendedRetailOpsState(TypedDict, total=False):
    """Extended state for 5-stage retail operations workflow"""
    # Telemetry metadata
    execution_id: str
    workflow_name: str
    start_time: str
    completed_steps: List[str]
    failed_steps: List[str]
    service_calls: List[Dict[str, Any]]

    # Input
    product_name: str
    days_ahead: int

    # Stage 1: Enrichment
    category: str
    brand: str
    description: str
    alternatives: List[Dict[str, Any]]
    enrichment_narrative: str

    # Stage 2: Forecasting
    forecast_data: Dict[str, Any]
    base_forecast: float
    final_forecast: float
    seasonal_multiplier: float
    event: str
    forecast_narrative: str

    # Stage 3: Replenishment
    replenishment_data: Dict[str, Any]
    reorder_qty: int
    reorder_timing: str
    stockout_risk: str
    replenishment_narrative: str

    # Stage 4: Supplier Intelligence (New 5th Capability)
    supplier_data: Dict[str, Any]
    supplier_id: str
    supplier_name: str
    reliability_score: float
    lead_time_days: int
    risk_category: str
    on_time_delivery_rate: float
    quality_rating: float
    cost_index: float
    recommended_supplier: str
    supplier_narrative: str

    # Stage 5: Pricing Strategy
    pricing_data: Dict[str, Any]
    current_price: float
    recommended_price: float
    price_change_pct: float
    recommendation_type: str
    pricing_narrative: str

    # Metadata
    errors: List[str]
    workflow_status: str
    timestamp: str


class ExtendedMCPServerManager(MCPServerManager):
    """
    Extends MCPServerManager to register the Supplier Intelligence MCP service.
    Reuses existing server configurations for enricher, forecasting, replenishment, and pricing.
    """

    def __init__(self):
        super().__init__()
        supplier_server = os.getenv(
            "RETAILOPS_SUPPLIER_SERVER_PATH",
            str(self.base_dir / "servers" / "supplier-intelligence" / "server.py")
        )
        self.servers["supplier"] = Path(supplier_server)

    def get_server_params(self, server_name: str) -> StdioServerParameters:
        if server_name == "supplier":
            server_env_var = "RETAILOPS_SUPPLIER_SERVER_PATH"
            if os.getenv(server_env_var):
                server_path = Path(os.getenv(server_env_var))
            else:
                server_path = self.servers["supplier"]

            if not server_path.exists():
                log(f"⚠️  Warning: Supplier server not found at {server_path}")

            server_env = os.environ.copy()
            server_env["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "")

            return StdioServerParameters(
                command=sys.executable,
                args=[str(server_path)],
                env=server_env
            )
        return super().get_server_params(server_name)

    async def call_supplier_intelligence(
        self,
        category: str,
        reorder_qty: Optional[int] = 100,
        telemetry_sink: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Call supplier intelligence MCP server"""
        log(f"🏭 Calling Supplier Intelligence for '{category}' (qty: {reorder_qty})")
        t_start_iso = now_iso()
        t_start = time.perf_counter()

        try:
            params = self.get_server_params("supplier")
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    response = await session.call_tool(
                        "getSupplierIntelligence",
                        {"category": category, "reorder_qty": int(reorder_qty or 100)}
                    )

                    if hasattr(response, 'content') and response.content:
                        for content in response.content:
                            if hasattr(content, 'text'):
                                result = json.loads(content.text)
                                log(f"✅ Supplier Intelligence received: {result.get('recommended_supplier')}")
                                if telemetry_sink is not None:
                                    t_dur = (time.perf_counter() - t_start) * 1000
                                    telemetry_sink.append(ServiceCallTelemetry(
                                        service_name="Supplier Intelligence",
                                        tool_name="getSupplierIntelligence",
                                        start_time=t_start_iso,
                                        end_time=now_iso(),
                                        duration_ms=round(t_dur, 2),
                                        status="success"
                                    ).to_dict())
                                return result

            err_msg = "No supplier data received"
            if telemetry_sink is not None:
                t_dur = (time.perf_counter() - t_start) * 1000
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Supplier Intelligence",
                    tool_name="getSupplierIntelligence",
                    start_time=t_start_iso,
                    end_time=now_iso(),
                    duration_ms=round(t_dur, 2),
                    status="failure",
                    error=err_msg
                ).to_dict())
            return {"error": err_msg}

        except Exception as e:
            log(f"❌ Supplier Intelligence error: {e}")
            if telemetry_sink is not None:
                t_dur = (time.perf_counter() - t_start) * 1000
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Supplier Intelligence",
                    tool_name="getSupplierIntelligence",
                    start_time=t_start_iso,
                    end_time=now_iso(),
                    duration_ms=round(t_dur, 2),
                    status="failure",
                    error=str(e)
                ).to_dict())
            return {"error": str(e)}


extended_server_manager = ExtendedMCPServerManager()


# =====================================================
# EXTENDED LANGGRAPH NODES
# =====================================================
async def extended_enrichment_node(state: ExtendedRetailOpsState) -> ExtendedRetailOpsState:
    log(f"🔵 NODE 1: Catalog Enrichment for '{state['product_name']}'")
    enrich_result = await extended_server_manager.call_enrichment(
        state["product_name"],
        telemetry_sink=state.get("service_calls")
    )
    if "error" in enrich_result:
        state["errors"].append(f"Enrichment: {enrich_result['error']}")
        state["failed_steps"].append("enrich")
        state["workflow_status"] = "failed_enrichment"
        state["category"] = "general"
        return state

    state["completed_steps"].append("enrich")
    state["category"] = enrich_result.get("category", "general")
    state["brand"] = enrich_result.get("brand", "Unknown")
    state["description"] = enrich_result.get("description", "")
    state["alternatives"] = enrich_result.get("alternatives", [])
    state["enrichment_narrative"] = enrich_result.get("narrative", "")
    return state


async def extended_forecasting_node(state: ExtendedRetailOpsState) -> ExtendedRetailOpsState:
    if "failed" in state.get("workflow_status", ""):
        return state

    category = state.get("category", "general")
    log(f"🔵 NODE 2: Forecasting for category '{category}'")
    days = int(state.get("days_ahead", 30))

    forecast_data = await extended_server_manager.call_forecasting(
        category,
        days,
        telemetry_sink=state.get("service_calls")
    )
    if "error" in forecast_data:
        state["errors"].append(f"Forecasting: {forecast_data['error']}")
        state["failed_steps"].append("forecast")
        state["workflow_status"] = "failed_forecast"
        return state

    state["completed_steps"].append("forecast")
    state["forecast_data"] = forecast_data
    state["base_forecast"] = forecast_data.get("base_forecast", 0)
    state["final_forecast"] = forecast_data.get("final_forecast", 0)
    state["seasonal_multiplier"] = forecast_data.get("seasonal_multiplier", 1.0)
    state["event"] = forecast_data.get("event", "None")
    state["forecast_narrative"] = forecast_data.get("narrative", "")
    return state


async def extended_replenishment_node(state: ExtendedRetailOpsState) -> ExtendedRetailOpsState:
    if "failed" in state.get("workflow_status", ""):
        return state

    log(f"🔵 NODE 3: Replenishment Decision")
    replenish_data = await extended_server_manager.call_replenishment(
        state["forecast_data"],
        current_stock=None,
        in_transit=None,
        telemetry_sink=state.get("service_calls")
    )
    if "error" in replenish_data:
        state["errors"].append(f"Replenishment: {replenish_data['error']}")
        state["failed_steps"].append("replenish")
        state["workflow_status"] = "failed_replenishment"
        return state

    state["completed_steps"].append("replenish")
    state["replenishment_data"] = replenish_data
    state["reorder_qty"] = replenish_data.get("reorder_qty", 0)
    state["reorder_timing"] = replenish_data.get("reorder_timing", "unknown")
    state["stockout_risk"] = replenish_data.get("stockout_risk", "unknown")
    state["replenishment_narrative"] = replenish_data.get("narrative", "")
    return state


async def supplier_intelligence_node(state: ExtendedRetailOpsState) -> ExtendedRetailOpsState:
    """Node 4: Get supplier intelligence (5th service)"""
    if "failed" in state.get("workflow_status", ""):
        return state

    log(f"🔵 NODE 4: Supplier Intelligence")
    category = state.get("category", "general")
    reorder_qty = state.get("reorder_qty", 100)

    sup_data = await extended_server_manager.call_supplier_intelligence(
        category=category,
        reorder_qty=reorder_qty,
        telemetry_sink=state.get("service_calls")
    )
    if "error" in sup_data:
        state["errors"].append(f"Supplier Intelligence: {sup_data['error']}")
        state["failed_steps"].append("supplier")
        state["workflow_status"] = "failed_supplier"
        return state

    state["completed_steps"].append("supplier")
    state["supplier_data"] = sup_data
    state["supplier_id"] = sup_data.get("supplier_id", "")
    state["supplier_name"] = sup_data.get("supplier_name", "")
    state["reliability_score"] = sup_data.get("reliability_score", 0.0)
    state["lead_time_days"] = sup_data.get("lead_time_days", 0)
    state["risk_category"] = sup_data.get("risk_category", "medium")
    state["on_time_delivery_rate"] = sup_data.get("on_time_delivery_rate", 0.0)
    state["quality_rating"] = sup_data.get("quality_rating", 0.0)
    state["cost_index"] = sup_data.get("cost_index", 1.0)
    state["recommended_supplier"] = sup_data.get("recommended_supplier", "")
    state["supplier_narrative"] = sup_data.get("narrative", "")
    return state


async def extended_pricing_node(state: ExtendedRetailOpsState) -> ExtendedRetailOpsState:
    """Node 5: Get pricing strategy"""
    if "failed" in state.get("workflow_status", ""):
        return state

    log(f"🔵 NODE 5: Pricing Strategy")
    pricing_data = await extended_server_manager.call_pricing(
        state["category"],
        state["final_forecast"],
        telemetry_sink=state.get("service_calls")
    )
    if "error" in pricing_data:
        state["errors"].append(f"Pricing: {pricing_data['error']}")
        state["failed_steps"].append("price")
        state["workflow_status"] = "failed_pricing"
        return state

    state["completed_steps"].append("price")
    state["pricing_data"] = pricing_data
    state["current_price"] = pricing_data.get("current_price", 0)
    state["recommended_price"] = pricing_data.get("recommended_price", 0)
    state["price_change_pct"] = pricing_data.get("price_change_pct", 0)
    state["recommendation_type"] = pricing_data.get("recommendation_type", "maintain")
    state["pricing_narrative"] = pricing_data.get("narrative", "")
    state["workflow_status"] = "completed"
    return state


def build_extended_retail_ops_graph():
    """Builds the extended 5-node LangGraph workflow"""
    workflow = StateGraph(ExtendedRetailOpsState)
    workflow.add_node("enrich", extended_enrichment_node)
    workflow.add_node("forecast", extended_forecasting_node)
    workflow.add_node("replenish", extended_replenishment_node)
    workflow.add_node("supplier", supplier_intelligence_node)
    workflow.add_node("price", extended_pricing_node)

    workflow.set_entry_point("enrich")
    workflow.add_edge("enrich", "forecast")
    workflow.add_edge("forecast", "replenish")
    workflow.add_edge("replenish", "supplier")
    workflow.add_edge("supplier", "price")
    workflow.add_edge("price", END)
    return workflow.compile()


class ExtendedRetailOpsClient:
    """Extended LangGraph client executing the 5-stage retail operations workflow."""

    def __init__(self, telemetry_logger: Optional[TelemetryLogger] = None):
        self.graph = build_extended_retail_ops_graph()
        self.telemetry_logger = telemetry_logger or TelemetryLogger()

    async def run_extended_workflow(self, product_name: str, days_ahead: int = 30) -> Dict[str, Any]:
        log(f"\n{'='*60}\n🎯 Starting Extended 5-Stage Workflow for '{product_name}'\n{'='*60}\n")

        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        workflow_name = "extended_mcp_orchestrator"
        start_time_iso = now_iso()
        t_start_perf = time.perf_counter()

        initial_state: ExtendedRetailOpsState = {
            "execution_id": execution_id,
            "workflow_name": workflow_name,
            "start_time": start_time_iso,
            "completed_steps": [],
            "failed_steps": [],
            "service_calls": [],
            "product_name": product_name,
            "days_ahead": int(days_ahead),
            "errors": [],
            "workflow_status": "running",
            "timestamp": datetime.now().isoformat()
        }

        try:
            final_state = await self.graph.ainvoke(initial_state)
            t_end_perf = time.perf_counter()
            end_time_iso = now_iso()
            total_duration_ms = round((t_end_perf - t_start_perf) * 1000, 2)

            result = {
                "execution_id": execution_id,
                "workflow_name": workflow_name,
                "start_time": start_time_iso,
                "end_time": end_time_iso,
                "total_duration_ms": total_duration_ms,
                "completed_steps": final_state.get("completed_steps", []),
                "failed_steps": final_state.get("failed_steps", []),
                "service_calls": final_state.get("service_calls", []),
                "product_name": product_name,
                "category": final_state.get("category"),
                "timestamp": final_state.get("timestamp"),
                "status": final_state.get("workflow_status"),
                "enrichment": {
                    "category": final_state.get("category"),
                    "brand": final_state.get("brand"),
                    "description": final_state.get("description"),
                    "narrative": final_state.get("enrichment_narrative")
                },
                "forecast": {
                    "final": final_state.get("final_forecast"),
                    "event": final_state.get("event"),
                    "narrative": final_state.get("forecast_narrative")
                },
                "replenishment": {
                    "reorder_qty": final_state.get("reorder_qty"),
                    "timing": final_state.get("reorder_timing"),
                    "narrative": final_state.get("replenishment_narrative")
                },
                "supplier_intelligence": {
                    "supplier_id": final_state.get("supplier_id"),
                    "supplier_name": final_state.get("supplier_name"),
                    "reliability_score": final_state.get("reliability_score"),
                    "lead_time_days": final_state.get("lead_time_days"),
                    "risk_category": final_state.get("risk_category"),
                    "on_time_delivery_rate": final_state.get("on_time_delivery_rate"),
                    "quality_rating": final_state.get("quality_rating"),
                    "cost_index": final_state.get("cost_index"),
                    "recommended_supplier": final_state.get("recommended_supplier"),
                    "narrative": final_state.get("supplier_narrative")
                },
                "pricing": {
                    "recommended_price": final_state.get("recommended_price"),
                    "change_pct": final_state.get("price_change_pct"),
                    "narrative": final_state.get("pricing_narrative")
                },
                "errors": final_state.get("errors", []),
                "architecture": "extended_mcp"
            }

            partial_result = {
                "category": final_state.get("category"),
                "enrichment": result["enrichment"],
                "forecast": result["forecast"],
                "replenishment": result["replenishment"],
                "supplier_intelligence": result["supplier_intelligence"],
                "pricing": result["pricing"]
            }
            result["partial_result"] = partial_result

            exec_telemetry = ExecutionTelemetry(
                execution_id=execution_id,
                workflow_name=workflow_name,
                product_name=product_name,
                category=final_state.get("category"),
                start_time=start_time_iso,
                end_time=end_time_iso,
                total_duration_ms=total_duration_ms,
                workflow_status=final_state.get("workflow_status", "unknown"),
                completed_steps=final_state.get("completed_steps", []),
                failed_steps=final_state.get("failed_steps", []),
                service_calls=final_state.get("service_calls", []),
                partial_result=partial_result,
                errors=final_state.get("errors", []),
                architecture="extended_mcp"
            )
            self.telemetry_logger.log_execution(exec_telemetry)

            return result

        except Exception as e:
            t_end_perf = time.perf_counter()
            end_time_iso = now_iso()
            total_duration_ms = round((t_end_perf - t_start_perf) * 1000, 2)
            log(f"💥 Extended Workflow Exception: {e}")
            return {
                "execution_id": execution_id,
                "workflow_name": workflow_name,
                "start_time": start_time_iso,
                "end_time": end_time_iso,
                "total_duration_ms": total_duration_ms,
                "completed_steps": initial_state.get("completed_steps", []),
                "failed_steps": initial_state.get("failed_steps", ["unknown"]),
                "service_calls": initial_state.get("service_calls", []),
                "product_name": product_name,
                "status": "crashed",
                "errors": [str(e)],
                "architecture": "extended_mcp"
            }
