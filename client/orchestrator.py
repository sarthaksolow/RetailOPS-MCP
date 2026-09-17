"""
RetailOps MCP Client - LangGraph Orchestrator
Efficiently chains:
Catalog Enricher → Forecasting → Replenishment → Pricing
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from typing import TypedDict, Annotated, Dict, Any, List
from datetime import datetime
import traceback

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession
from typing import Optional

import uuid
import time
try:
    from .telemetry import ServiceCallTelemetry, ExecutionTelemetry, TelemetryLogger, now_iso
except ImportError:
    from telemetry import ServiceCallTelemetry, ExecutionTelemetry, TelemetryLogger, now_iso

# Load environment
load_dotenv()

# Logging
def log(msg: str):
    print(f"[CLIENT] {msg}", file=sys.stderr, flush=True)

log(">>> Initializing RetailOps LangGraph Client")


# =====================================================
# STATE DEFINITION
# =====================================================
class RetailOpsState(TypedDict):
    """Complete state for retail operations workflow"""
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
    
    # Enrichment outputs
    category: str
    brand: str
    description: str
    alternatives: List[Dict[str, Any]]
    enrichment_narrative: str
    
    # Forecasting outputs
    forecast_data: Dict[str, Any]
    base_forecast: float
    final_forecast: float
    seasonal_multiplier: float
    event: str
    forecast_narrative: str
    
    # Replenishment outputs
    replenishment_data: Dict[str, Any]
    reorder_qty: int
    reorder_timing: str
    stockout_risk: str
    replenishment_narrative: str
    
    # Pricing outputs
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


# =====================================================
# MCP SERVER CONNECTIONS
# =====================================================
class MCPServerManager:
    """Manages connections to all MCP servers"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.servers = {
            "enricher": self.base_dir / "servers" / "catalog-enricher" / "server.py",
            "forecasting": self.base_dir / "servers" / "forecasting" / "server.py",
            "replenishment": self.base_dir / "servers" / "replenishment" / "server.py",
            "pricing": self.base_dir / "servers" / "pricing-strategy" / "server.py"
        }
        
    def get_server_params(self, server_name: str) -> StdioServerParameters:
        """Get server parameters for MCP connection"""
        server_path = self.servers[server_name]
        if not server_path.exists():
            log(f"⚠️  Warning: Server not found at {server_path}")
            
        return StdioServerParameters(
            command=sys.executable,
            args=[str(server_path)],
            env={"OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", "")}
        )

    async def call_enrichment(self, product_name: str, telemetry_sink: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Call catalog enricher server"""
        log(f"🧹 Calling Catalog Enricher for '{product_name}'")
        t_start_iso = now_iso()
        t_start = time.perf_counter()
        
        try:
            params = self.get_server_params("enricher")
            
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    response = await session.call_tool(
                        "enrichProduct",
                        {
                            "input": {
                                "product_name": product_name,
                                "product_data": {} 
                            }
                        }
                    )
                    
                    if hasattr(response, 'content') and response.content:
                        for content in response.content:
                            if hasattr(content, 'text'):
                                result = json.loads(content.text)
                                log(f"✅ Enriched: Mapped to category '{result.get('category')}'")
                                if telemetry_sink is not None:
                                    t_dur = (time.perf_counter() - t_start) * 1000
                                    telemetry_sink.append(ServiceCallTelemetry(
                                        service_name="Catalog Enricher",
                                        tool_name="enrichProduct",
                                        start_time=t_start_iso,
                                        end_time=now_iso(),
                                        duration_ms=round(t_dur, 2),
                                        status="success"
                                    ).to_dict())
                                return result
            
            err_msg = "No enrichment data received"
            if telemetry_sink is not None:
                t_dur = (time.perf_counter() - t_start) * 1000
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Catalog Enricher",
                    tool_name="enrichProduct",
                    start_time=t_start_iso,
                    end_time=now_iso(),
                    duration_ms=round(t_dur, 2),
                    status="failure",
                    error=err_msg
                ).to_dict())
            return {"error": err_msg}
            
        except Exception as e:
            log(f"❌ Enrichment error: {e}")
            if telemetry_sink is not None:
                t_dur = (time.perf_counter() - t_start) * 1000
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Catalog Enricher",
                    tool_name="enrichProduct",
                    start_time=t_start_iso,
                    end_time=now_iso(),
                    duration_ms=round(t_dur, 2),
                    status="failure",
                    error=str(e)
                ).to_dict())
            return {"error": str(e)}
    
    async def call_forecasting(self, category: str, days_ahead: int = 30, telemetry_sink: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Call forecasting server"""
        log(f"📊 Calling Forecasting Server for {category}")
        t_start_iso = now_iso()
        t_start = time.perf_counter()
        
        try:
            # Type safety
            safe_days = int(days_ahead) if days_ahead is not None else 30
            
            params = self.get_server_params("forecasting")
            
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    response = await session.call_tool(
                        "getForecast",
                        {"category": category, "days_ahead": safe_days}
                    )
                    
                    if hasattr(response, 'content') and response.content:
                        for content in response.content:
                            if hasattr(content, 'text'):
                                result = json.loads(content.text)
                                log(f"✅ Forecast received: {result.get('final_forecast')}")
                                if "error" in result:
                                    if telemetry_sink is not None:
                                        t_dur = (time.perf_counter() - t_start) * 1000
                                        telemetry_sink.append(ServiceCallTelemetry(
                                            service_name="Forecasting",
                                            tool_name="getForecast",
                                            start_time=t_start_iso,
                                            end_time=now_iso(),
                                            duration_ms=round(t_dur, 2),
                                            status="failure",
                                            error=result["error"]
                                        ).to_dict())
                                    return result
                                if telemetry_sink is not None:
                                    t_dur = (time.perf_counter() - t_start) * 1000
                                    telemetry_sink.append(ServiceCallTelemetry(
                                        service_name="Forecasting",
                                        tool_name="getForecast",
                                        start_time=t_start_iso,
                                        end_time=now_iso(),
                                        duration_ms=round(t_dur, 2),
                                        status="success"
                                    ).to_dict())
                                return result
            
            err_msg = "No forecast data received"
            if telemetry_sink is not None:
                t_dur = (time.perf_counter() - t_start) * 1000
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Forecasting",
                    tool_name="getForecast",
                    start_time=t_start_iso,
                    end_time=now_iso(),
                    duration_ms=round(t_dur, 2),
                    status="failure",
                    error=err_msg
                ).to_dict())
            return {"error": err_msg}
            
        except Exception as e:
            err_msg = str(e)
            if "TaskGroup" in err_msg or "subprocess" in err_msg:
                log(f"❌ Forecasting Server Crash: {err_msg}")
            else:
                log(f"❌ Forecasting error: {err_msg}")
            if telemetry_sink is not None:
                t_dur = (time.perf_counter() - t_start) * 1000
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Forecasting",
                    tool_name="getForecast",
                    start_time=t_start_iso,
                    end_time=now_iso(),
                    duration_ms=round(t_dur, 2),
                    status="failure",
                    error=err_msg
                ).to_dict())
            return {"error": err_msg}
    
    async def call_replenishment(self, forecast_data: Dict[str, Any], 
                                  current_stock: int = None,
                                  in_transit: int = None,
                                  telemetry_sink: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Call replenishment server"""
        log(f"📦 Calling Replenishment Server")
        t_start_iso = now_iso()
        t_start = time.perf_counter()
        
        # Realistic inventory levels
        inventory_levels = {
            "tv": {"current": 45, "in_transit": 10},
            "laptop": {"current": 25, "in_transit": 5},
            "phone": {"current": 80, "in_transit": 20},
            "electronics": {"current": 150, "in_transit": 50},
            "fashion": {"current": 350, "in_transit": 50},
            "groceries": {"current": 800, "in_transit": 200},
        }
        
        category = forecast_data.get("category", "general")
        inv = inventory_levels.get(category, {"current": 200, "in_transit": 50})
        
        if current_stock is None:
            current_stock = inv["current"]
        if in_transit is None:
            in_transit = inv["in_transit"]
        
        try:
            replenish_input = {
                "category": category,
                "forecast": {
                    "forecasted_demand": forecast_data.get("final_forecast"),
                    "avg_daily_demand": forecast_data.get("final_forecast", 0) / 30,
                    "demand_volatility": "medium",
                    "event": {
                        "name": forecast_data.get("event"),
                        "days_to_event": 10 if forecast_data.get("event") else None
                    }
                },
                "inventory": {
                    "current_stock": current_stock,
                    "in_transit_stock": in_transit
                },
                "supplier": {
                    "lead_time_days": 10,
                    "minimum_order_quantity": 50
                }
            }
            
            params = self.get_server_params("replenishment")
            
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    response = await session.call_tool(
                        "getReplenishmentDecision",
                        {"input": replenish_input}
                    )
                    
                    if hasattr(response, 'content') and response.content:
                        for content in response.content:
                            if hasattr(content, 'text'):
                                result = json.loads(content.text)
                                log(f"✅ Replenishment: {result.get('reorder_qty')} units")
                                if "error" in result:
                                    if telemetry_sink is not None:
                                        t_dur = (time.perf_counter() - t_start) * 1000
                                        telemetry_sink.append(ServiceCallTelemetry(
                                            service_name="Replenishment",
                                            tool_name="getReplenishmentDecision",
                                            start_time=t_start_iso,
                                            end_time=now_iso(),
                                            duration_ms=round(t_dur, 2),
                                            status="failure",
                                            error=result["error"]
                                        ).to_dict())
                                    return result
                                if telemetry_sink is not None:
                                    t_dur = (time.perf_counter() - t_start) * 1000
                                    telemetry_sink.append(ServiceCallTelemetry(
                                        service_name="Replenishment",
                                        tool_name="getReplenishmentDecision",
                                        start_time=t_start_iso,
                                        end_time=now_iso(),
                                        duration_ms=round(t_dur, 2),
                                        status="success"
                                    ).to_dict())
                                return result
            
            err_msg = "No replenishment data received"
            if telemetry_sink is not None:
                t_dur = (time.perf_counter() - t_start) * 1000
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Replenishment",
                    tool_name="getReplenishmentDecision",
                    start_time=t_start_iso,
                    end_time=now_iso(),
                    duration_ms=round(t_dur, 2),
                    status="failure",
                    error=err_msg
                ).to_dict())
            return {"error": err_msg}
            
        except Exception as e:
            log(f"❌ Replenishment error: {e}")
            if telemetry_sink is not None:
                t_dur = (time.perf_counter() - t_start) * 1000
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Replenishment",
                    tool_name="getReplenishmentDecision",
                    start_time=t_start_iso,
                    end_time=now_iso(),
                    duration_ms=round(t_dur, 2),
                    status="failure",
                    error=str(e)
                ).to_dict())
            return {"error": str(e)}
    
    async def call_pricing(self, category: str, 
                          forecasted_demand: float,
                          inventory_level: int = None,
                          current_price: float = None,
                          telemetry_sink: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Call pricing strategy server"""
        log(f"💰 Calling Pricing Strategy Server")
        t_start_iso = now_iso()
        t_start = time.perf_counter()
        
        # Default prices
        default_prices = {
            "electronics": 9000,
            "tv": 28000,
            "laptop": 48000,
            "phone": 16000,
            "kitchen_appliances": 5500,
            "fashion": 1500,
            "groceries": 220,
        }
        
        if current_price is None:
            current_price = default_prices.get(category, 5000)
            
        inventory_level = inventory_level or 100
        
        try:
            pricing_input = {
                "category": category,
                "current_price": current_price,
                "forecasted_demand": forecasted_demand,
                "inventory_level": inventory_level,
                "target_profit_pct": 0
            }
            
            params = self.get_server_params("pricing")
            
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    response = await session.call_tool(
                        "getPricingStrategy",
                        {"input": pricing_input}
                    )
                    
                    if hasattr(response, 'content') and response.content:
                        for content in response.content:
                            if hasattr(content, 'text'):
                                result = json.loads(content.text)
                                log(f"✅ Pricing: ₹{result.get('recommended_price')}")
                                if "error" in result:
                                    if telemetry_sink is not None:
                                        t_dur = (time.perf_counter() - t_start) * 1000
                                        telemetry_sink.append(ServiceCallTelemetry(
                                            service_name="Pricing Strategy",
                                            tool_name="getPricingStrategy",
                                            start_time=t_start_iso,
                                            end_time=now_iso(),
                                            duration_ms=round(t_dur, 2),
                                            status="failure",
                                            error=result["error"]
                                        ).to_dict())
                                    return result
                                if telemetry_sink is not None:
                                    t_dur = (time.perf_counter() - t_start) * 1000
                                    telemetry_sink.append(ServiceCallTelemetry(
                                        service_name="Pricing Strategy",
                                        tool_name="getPricingStrategy",
                                        start_time=t_start_iso,
                                        end_time=now_iso(),
                                        duration_ms=round(t_dur, 2),
                                        status="success"
                                    ).to_dict())
                                return result
            
            err_msg = "No pricing data received"
            if telemetry_sink is not None:
                t_dur = (time.perf_counter() - t_start) * 1000
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Pricing Strategy",
                    tool_name="getPricingStrategy",
                    start_time=t_start_iso,
                    end_time=now_iso(),
                    duration_ms=round(t_dur, 2),
                    status="failure",
                    error=err_msg
                ).to_dict())
            return {"error": err_msg}
            
        except Exception as e:
            log(f"❌ Pricing error: {e}")
            if telemetry_sink is not None:
                t_dur = (time.perf_counter() - t_start) * 1000
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Pricing Strategy",
                    tool_name="getPricingStrategy",
                    start_time=t_start_iso,
                    end_time=now_iso(),
                    duration_ms=round(t_dur, 2),
                    status="failure",
                    error=str(e)
                ).to_dict())
            return {"error": str(e)}


# =====================================================
# LANGGRAPH NODES
# =====================================================
server_manager = MCPServerManager()

async def enrichment_node(state: RetailOpsState) -> RetailOpsState:
    """Node 1: Enrich product and determine category"""
    log(f"🔵 NODE 1: Catalog Enrichment for '{state['product_name']}'")
    
    enrich_result = await server_manager.call_enrichment(
        state["product_name"],
        telemetry_sink=state.get("service_calls")
    )
    
    if "error" in enrich_result:
        state["errors"].append(f"Enrichment: {enrich_result['error']}")
        state["failed_steps"].append("enrich")
        state["category"] = "general"
        return state

    state["completed_steps"].append("enrich")
    state["category"] = enrich_result.get("category", "general")
    state["brand"] = enrich_result.get("brand", "Unknown")
    state["description"] = enrich_result.get("description", "")
    state["alternatives"] = enrich_result.get("alternatives", [])
    state["enrichment_narrative"] = enrich_result.get("narrative", "")
    return state

async def forecasting_node(state: RetailOpsState) -> RetailOpsState:
    """Node 2: Get demand forecast"""
    category = state.get("category", "general")
    log(f"🔵 NODE 2: Forecasting for category '{category}'")
    
    # Cast days_ahead to int just in case
    days = int(state.get("days_ahead", 30))
    
    forecast_data = await server_manager.call_forecasting(
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

async def replenishment_node(state: RetailOpsState) -> RetailOpsState:
    """Node 3: Get replenishment decision"""
    log(f"🔵 NODE 3: Replenishment Decision")
    
    if state.get("workflow_status") == "failed_forecast":
        return state
    
    replenish_data = await server_manager.call_replenishment(
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

async def pricing_node(state: RetailOpsState) -> RetailOpsState:
    """Node 4: Get pricing strategy"""
    log(f"🔵 NODE 4: Pricing Strategy")
    
    if "failed" in state.get("workflow_status", ""):
        return state
    
    pricing_data = await server_manager.call_pricing(
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


# =====================================================
# GRAPH & CLIENT
# =====================================================
def build_retail_ops_graph():
    workflow = StateGraph(RetailOpsState)
    workflow.add_node("enrich", enrichment_node)
    workflow.add_node("forecast", forecasting_node)
    workflow.add_node("replenish", replenishment_node)
    workflow.add_node("price", pricing_node)
    workflow.set_entry_point("enrich")
    workflow.add_edge("enrich", "forecast")
    workflow.add_edge("forecast", "replenish")
    workflow.add_edge("replenish", "price")
    workflow.add_edge("price", END)
    return workflow.compile()

class RetailOpsClient:
    def __init__(self, telemetry_logger: Optional[TelemetryLogger] = None):
        self.graph = build_retail_ops_graph()
        self.telemetry_logger = telemetry_logger or TelemetryLogger()
    
    async def run_full_workflow(self, product_name: str, days_ahead: int = 30) -> Dict[str, Any]:
        log(f"\n{'='*60}\n🎯 Starting Full Workflow for '{product_name}'\n{'='*60}\n")
        
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        workflow_name = "retail_operations_orchestrator"
        start_time_iso = now_iso()
        t_start_perf = time.perf_counter()
        
        initial_state = RetailOpsState(
            execution_id=execution_id,
            workflow_name=workflow_name,
            start_time=start_time_iso,
            completed_steps=[],
            failed_steps=[],
            service_calls=[],
            product_name=product_name,
            days_ahead=int(days_ahead),
            errors=[],
            workflow_status="running",
            timestamp=datetime.now().isoformat()
        )
        
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
                "category": final_state.get("category"), # ROOT LEVEL
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
                "pricing": {
                    "recommended_price": final_state.get("recommended_price"),
                    "change_pct": final_state.get("price_change_pct"),
                    "narrative": final_state.get("pricing_narrative")
                },
                "errors": final_state.get("errors", [])
            }
            
            # Partial result snapshot containing completed outputs
            partial_result = {
                "category": final_state.get("category"),
                "enrichment": result["enrichment"],
                "forecast": result["forecast"],
                "replenishment": result["replenishment"],
                "pricing": result["pricing"]
            }
            result["partial_result"] = partial_result
            
            # Log telemetry
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
                errors=final_state.get("errors", [])
            )
            self.telemetry_logger.log_execution(exec_telemetry)
            
            log(f"\n{'='*60}\n✅ Workflow Completed: {result['status']}\n{'='*60}\n")
            return result
        except Exception as e:
            t_end_perf = time.perf_counter()
            end_time_iso = now_iso()
            total_duration_ms = round((t_end_perf - t_start_perf) * 1000, 2)
            log(f"❌ Workflow failed: {e}")
            
            err_result = {
                "execution_id": execution_id,
                "workflow_name": workflow_name,
                "start_time": start_time_iso,
                "end_time": end_time_iso,
                "total_duration_ms": total_duration_ms,
                "completed_steps": [],
                "failed_steps": ["workflow_execution"],
                "service_calls": [],
                "product_name": product_name,
                "category": None,
                "status": "error",
                "error": str(e),
                "errors": [str(e)],
                "partial_result": {}
            }
            exec_telemetry = ExecutionTelemetry(
                execution_id=execution_id,
                workflow_name=workflow_name,
                product_name=product_name,
                category=None,
                start_time=start_time_iso,
                end_time=end_time_iso,
                total_duration_ms=total_duration_ms,
                workflow_status="error",
                completed_steps=[],
                failed_steps=["workflow_execution"],
                service_calls=[],
                partial_result={},
                errors=[str(e)]
            )
            self.telemetry_logger.log_execution(exec_telemetry)
            return err_result

    # Helper methods restored for tests/NLP
    async def run_forecast_only(self, category: str, days_ahead: int = 30) -> Dict[str, Any]:
        """Direct call to forecasting server"""
        return await server_manager.call_forecasting(category, int(days_ahead))

    async def run_batch_workflow(self, product_names: List[str], days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Run workflow in parallel"""
        log(f"\n🔄 Running batch workflow for {len(product_names)} products")
        tasks = [self.run_full_workflow(name, days_ahead) for name in product_names]
        return await asyncio.gather(*tasks)

if __name__ == "__main__":
    _product = os.getenv("RETAILOPS_DEFAULT_PRODUCT", "Samsung TV")
    _days    = int(os.getenv("RETAILOPS_DEFAULT_DAYS", "30"))
    asyncio.run(RetailOpsClient().run_full_workflow(_product, _days))