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

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession
from typing import Optional

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
    # Input
    product_name: str  # New entry input
    days_ahead: int
    
    # Enrichment outputs (New)
    category: str      # Derived from enrichment
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

    async def call_enrichment(self, product_name: str) -> Dict[str, Any]:
        """Call catalog enricher server"""
        log(f"🧹 Calling Catalog Enricher for '{product_name}'")
        
        try:
            params = self.get_server_params("enricher")
            
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Matches the structure from your working unit test
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
                                return result
            
            return {"error": "No enrichment data received"}
            
        except Exception as e:
            log(f"❌ Enrichment error: {e}")
            return {"error": str(e)}
    
    async def call_forecasting(self, category: str, days_ahead: int = 30) -> Dict[str, Any]:
        """Call forecasting server"""
        log(f"📊 Calling Forecasting Server for {category}")
        
        try:
            params = self.get_server_params("forecasting")
            
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    response = await session.call_tool(
                        "getForecast",
                        {"category": category, "days_ahead": days_ahead}
                    )
                    
                    if hasattr(response, 'content') and response.content:
                        for content in response.content:
                            if hasattr(content, 'text'):
                                result = json.loads(content.text)
                                log(f"✅ Forecast received: {result.get('final_forecast')}")
                                return result
            
            return {"error": "No forecast data received"}
            
        except Exception as e:
            log(f"❌ Forecasting error: {e}")
            return {"error": str(e)}
    
    async def call_replenishment(self, forecast_data: Dict[str, Any], 
                                  current_stock: int = None,
                                  in_transit: int = None) -> Dict[str, Any]:
        """Call replenishment server"""
        log(f"📦 Calling Replenishment Server")
        
        # Realistic inventory levels by category
        inventory_levels = {
            "tv": {"current": 45, "in_transit": 10},
            "laptop": {"current": 25, "in_transit": 5},
            "phone": {"current": 80, "in_transit": 20},
            "kitchen_appliances": {"current": 120, "in_transit": 30},
            "fashion": {"current": 350, "in_transit": 50},
            "groceries": {"current": 800, "in_transit": 200},
            "electronics": {"current": 450, "in_transit": 100},
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
                                return result
            
            return {"error": "No replenishment data received"}
            
        except Exception as e:
            log(f"❌ Replenishment error: {e}")
            return {"error": str(e)}
    
    async def call_pricing(self, category: str, 
                          forecasted_demand: float,
                          inventory_level: int = None,
                          current_price: float = None) -> Dict[str, Any]:
        """Call pricing strategy server"""
        log(f"💰 Calling Pricing Strategy Server")
        
        # Default prices by category
        default_prices = {
            "electronics": 9000,
            "tv": 28000,
            "laptop": 48000,
            "phone": 16000,
            "kitchen_appliances": 5500,
            "fashion": 1500,
            "groceries": 220,
            "general": 1000
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
                                return result
            
            return {"error": "No pricing data received"}
            
        except Exception as e:
            log(f"❌ Pricing error: {e}")
            return {"error": str(e)}


# =====================================================
# LANGGRAPH NODES
# =====================================================
server_manager = MCPServerManager()

async def enrichment_node(state: RetailOpsState) -> RetailOpsState:
    """Node 1: Enrich product and determine category"""
    log(f"🔵 NODE 1: Catalog Enrichment for '{state['product_name']}'")
    
    enrich_result = await server_manager.call_enrichment(state["product_name"])
    
    if "error" in enrich_result:
        state["errors"].append(f"Enrichment: {enrich_result['error']}")
        # Fallback if enrichment fails
        state["category"] = "general"
        return state

    # Update state
    state["category"] = enrich_result.get("category", "general")
    state["brand"] = enrich_result.get("brand", "Unknown")
    state["description"] = enrich_result.get("description", "")
    state["alternatives"] = enrich_result.get("alternatives", [])
    state["enrichment_narrative"] = enrich_result.get("narrative", "")
    
    return state

async def forecasting_node(state: RetailOpsState) -> RetailOpsState:
    """Node 2: Get demand forecast using derived category"""
    category = state.get("category", "general")
    log(f"🔵 NODE 2: Forecasting for category '{category}'")
    
    forecast_data = await server_manager.call_forecasting(
        category,
        state.get("days_ahead", 30)
    )
    
    if "error" in forecast_data:
        state["errors"].append(f"Forecasting: {forecast_data['error']}")
        state["workflow_status"] = "failed_forecast"
        return state
    
    # Update state
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
    
    # Skip if forecast failed
    if state.get("workflow_status") == "failed_forecast":
        return state
    
    replenish_data = await server_manager.call_replenishment(
        state["forecast_data"],
        current_stock=None,
        in_transit=None
    )
    
    if "error" in replenish_data:
        state["errors"].append(f"Replenishment: {replenish_data['error']}")
        state["workflow_status"] = "failed_replenishment"
        return state
    
    # Update state
    state["replenishment_data"] = replenish_data
    state["reorder_qty"] = replenish_data.get("reorder_qty", 0)
    state["reorder_timing"] = replenish_data.get("reorder_timing", "unknown")
    state["stockout_risk"] = replenish_data.get("stockout_risk", "unknown")
    state["replenishment_narrative"] = replenish_data.get("narrative", "")
    
    return state


async def pricing_node(state: RetailOpsState) -> RetailOpsState:
    """Node 4: Get pricing strategy"""
    log(f"🔵 NODE 4: Pricing Strategy")
    
    # Skip if previous nodes failed
    if "failed" in state.get("workflow_status", ""):
        return state
    
    pricing_data = await server_manager.call_pricing(
        state["category"],
        state["final_forecast"],
        inventory_level=None
    )
    
    if "error" in pricing_data:
        state["errors"].append(f"Pricing: {pricing_data['error']}")
        state["workflow_status"] = "failed_pricing"
        return state
    
    # Update state
    state["pricing_data"] = pricing_data
    state["current_price"] = pricing_data.get("current_price", 0)
    state["recommended_price"] = pricing_data.get("recommended_price", 0)
    state["price_change_pct"] = pricing_data.get("price_change_pct", 0)
    state["recommendation_type"] = pricing_data.get("recommendation_type", "maintain")
    state["pricing_narrative"] = pricing_data.get("narrative", "")
    
    state["workflow_status"] = "completed"
    return state


# =====================================================
# BUILD LANGGRAPH
# =====================================================
def build_retail_ops_graph():
    """Build the orchestration graph"""
    log("🔨 Building LangGraph workflow")
    
    workflow = StateGraph(RetailOpsState)
    
    # Add nodes
    workflow.add_node("enrich", enrichment_node)
    workflow.add_node("forecast", forecasting_node)
    workflow.add_node("replenish", replenishment_node)
    workflow.add_node("price", pricing_node)
    
    # Set entry point
    workflow.set_entry_point("enrich")
    
    # Add edges (sequential flow)
    workflow.add_edge("enrich", "forecast")
    workflow.add_edge("forecast", "replenish")
    workflow.add_edge("replenish", "price")
    workflow.add_edge("price", END)
    
    # Compile
    graph = workflow.compile()
    log("✅ Graph compiled successfully")
    
    return graph


# =====================================================
# CLIENT API
# =====================================================
class RetailOpsClient:
    """Main client interface"""
    
    def __init__(self):
        self.graph = build_retail_ops_graph()
        log("🚀 RetailOps Client initialized")
    
    async def run_full_workflow(self, product_name: str, days_ahead: int = 30) -> Dict[str, Any]:
        """Run complete workflow: Enrich → Forecast → Replenish → Price"""
        log(f"\n{'='*60}")
        log(f"🎯 Starting Full Workflow for '{product_name}'")
        log(f"{'='*60}\n")
        
        # Initialize state
        initial_state = RetailOpsState(
            product_name=product_name,
            days_ahead=days_ahead,
            errors=[],
            workflow_status="running",
            timestamp=datetime.now().isoformat()
        )
        
        # Run workflow
        try:
            final_state = await self.graph.ainvoke(initial_state)
            
            # Format results
            result = {
                "product_name": product_name,
                "category": final_state.get("category", "unknown"),  # Added to root for test compatibility
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
            
            log(f"\n{'='*60}")
            log(f"✅ Workflow Completed: {result['status']}")
            log(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            log(f"❌ Workflow failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "product_name": product_name,
                "status": "error",
                "error": str(e)
            }
            
    async def run_forecast_only(self, category: str, days_ahead: int = 30) -> Dict[str, Any]:
        """Run only forecasting (helper method for tests)"""
        return await server_manager.call_forecasting(category, days_ahead)
    
    async def run_batch_workflow(self, product_names: List[str], days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Run workflow for multiple products in parallel"""
        log(f"\n🔄 Running batch workflow for {len(product_names)} products")
        
        tasks = [self.run_full_workflow(name, days_ahead) for name in product_names]
        results = await asyncio.gather(*tasks)
        
        log(f"✅ Batch processing complete")
        return results


# =====================================================
# CLI INTERFACE
# =====================================================
async def main():
    """CLI entry point"""
    print("\n" + "="*60)
    print("🛍️  RetailOps MCP Client - LangGraph Orchestrator")
    print("="*60 + "\n")
    
    client = RetailOpsClient()
    
    # Example: Run full workflow for a specific product
    # The enricher should map this to 'tv' or 'electronics' automatically
    product_input = "Samsung 55 inch Smart TV"
    
    result = await client.run_full_workflow(product_input, days_ahead=30)
    
    # Pretty print results
    print("\n📊 RESULTS:")
    print("="*60)
    print(json.dumps(result, indent=2))
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())