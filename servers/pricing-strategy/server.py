import os
import sys
import json
from typing import TypedDict, Dict, Any, List
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from langgraph.graph import StateGraph
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# -------------------------------------------------
# STDIO-safe logging (IMPORTANT)
# -------------------------------------------------
def log(msg: str):
    print(msg, file=sys.stderr, flush=True)

log(">>> Loading Pricing Strategy MCP Server")

# -------------------------------------------------
# OpenRouter Client (FREE API)
# -------------------------------------------------
api_key = os.getenv("OPENROUTER_API_KEY")
if api_key:
    log(">>> OpenRouter API configured")
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "http://localhost",
            "X-Title": "Pricing Strategy Reasoning Engine"
        }
    )
else:
    log("⚠️ WARNING: OPENROUTER_API_KEY not set")
    client = None

# -------------------------------------------------
# MCP Init
# -------------------------------------------------
mcp = FastMCP("pricing-strategy-server")

# -------------------------------------------------
# Load Data
# -------------------------------------------------
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    log(f"BASE_DIR: {BASE_DIR}")

    elasticity_path = os.path.join(BASE_DIR, "data", "price_elasticity.json")
    competitor_path = os.path.join(BASE_DIR, "data", "competitor_prices.json")

    log(f"Elasticity path: {elasticity_path}")
    log(f"Competitor path: {competitor_path}")

    with open(elasticity_path, "r") as f:
        elasticity_data = json.load(f)
    log(f">>> Elasticity data loaded: {len(elasticity_data)} categories")

    with open(competitor_path, "r") as f:
        competitor_data = json.load(f)
    log(f">>> Competitor data loaded: {len(competitor_data)} categories")

except Exception as e:
    log(f"⚠️ Startup error loading files: {e}")
    import traceback
    traceback.print_exc(file=sys.stderr)
    raise SystemExit(1)

# -------------------------------------------------
# LangGraph State
# -------------------------------------------------
class PricingState(TypedDict):
    input: Dict[str, Any]

    category: str
    current_price: float
    forecasted_demand: float
    inventory_level: float
    target_profit_pct: float
    
    elasticity: float
    base_margin: float
    min_margin: float
    max_discount: float
    
    competitor_price: float
    price_difference_pct: float
    
    demand_elasticity_impact: float
    margin_impact: float
    competitor_position: str
    
    recommended_price: float
    price_change_pct: float
    expected_demand_change: float
    expected_revenue_change: float
    expected_profit_change: float
    
    recommendation_type: str
    explanation_factors: List[str]
    narrative: str

# -------------------------------------------------
# Graph Nodes
# -------------------------------------------------
def load_category_data_node(state: PricingState):
    """Load category-specific pricing data"""
    category = state["input"]["category"]
    
    # Load elasticity data
    cat_elasticity = elasticity_data.get(category, {})
    state["category"] = category
    state["elasticity"] = cat_elasticity.get("elasticity", -1.5)
    state["base_margin"] = cat_elasticity.get("base_margin", 0.20)
    state["min_margin"] = cat_elasticity.get("min_margin", 0.15)
    state["max_discount"] = cat_elasticity.get("max_discount", 0.20)
    
    # Load competitor data
    cat_competitor = competitor_data.get(category, {})
    state["competitor_price"] = cat_competitor.get("competitor_avg_price", state["input"].get("current_price", 1000))
    state["price_difference_pct"] = cat_competitor.get("price_difference_pct", 0.0)
    
    # Extract input data
    state["current_price"] = state["input"].get("current_price", state["competitor_price"] * 1.1)
    state["forecasted_demand"] = state["input"].get("forecasted_demand", 100)
    state["inventory_level"] = state["input"].get("inventory_level", 200)
    state["target_profit_pct"] = state["input"].get("target_profit_pct", 0.0)
    
    state["explanation_factors"] = []
    return state


def analyze_competitor_position_node(state: PricingState):
    """Analyze competitive pricing position"""
    price_diff = state["price_difference_pct"]
    
    if price_diff > 15:
        state["competitor_position"] = "overpriced"
        state["explanation_factors"].append(f"we are {price_diff:.1f}% above competitor average")
    elif price_diff > 5:
        state["competitor_position"] = "slightly_high"
        state["explanation_factors"].append(f"we are {price_diff:.1f}% above competitor average")
    elif price_diff < -5:
        state["competitor_position"] = "undervalued"
        state["explanation_factors"].append(f"we are {abs(price_diff):.1f}% below competitor average")
    else:
        state["competitor_position"] = "competitive"
        state["explanation_factors"].append("pricing is competitive with market")
    
    return state


def calculate_elasticity_impact_node(state: PricingState):
    """Calculate demand impact based on price elasticity"""
    elasticity = state["elasticity"]
    # Elasticity formula: % change in demand = elasticity * % change in price
    # We'll calculate this in the pricing decision node
    state["demand_elasticity_impact"] = abs(elasticity)
    state["explanation_factors"].append(f"price elasticity is {elasticity:.1f} (demand is {'elastic' if abs(elasticity) > 1 else 'inelastic'})")
    return state


def inventory_pressure_node(state: PricingState):
    """Analyze inventory pressure"""
    inventory = state["inventory_level"]
    forecasted = state["forecasted_demand"]
    
    inventory_ratio = inventory / forecasted if forecasted > 0 else 1.0
    
    if inventory_ratio > 2.0:
        state["explanation_factors"].append("high inventory levels (overstocked)")
    elif inventory_ratio < 0.5:
        state["explanation_factors"].append("low inventory levels (risk of stockout)")
    else:
        state["explanation_factors"].append("inventory levels are balanced")
    
    return state


def pricing_decision_node(state: PricingState):
    """Make pricing decision based on all factors"""
    current_price = state["current_price"]
    elasticity = state["elasticity"]
    base_margin = state["base_margin"]
    min_margin = state["min_margin"]
    competitor_price = state["competitor_price"]
    competitor_pos = state["competitor_position"]
    target_profit = state["target_profit_pct"]
    forecasted_demand = state["forecasted_demand"]
    inventory_ratio = state["inventory_level"] / forecasted_demand if forecasted_demand > 0 else 1.0
    
    # Initialize recommendation
    recommended_price = current_price
    price_change_pct = 0.0
    recommendation_type = "maintain"
    
    # Decision logic
    factors = []
    
    # Factor 1: Competitor positioning
    if competitor_pos == "overpriced":
        # Reduce price to be more competitive
        price_reduction = min(0.10, state["max_discount"])  # Max 10% or category max
        recommended_price = current_price * (1 - price_reduction)
        price_change_pct = -price_reduction * 100
        recommendation_type = "discount"
        factors.append("reduce price to match competition")
    elif competitor_pos == "undervalued" and target_profit > 0:
        # Increase price if we need profit and are undervalued
        price_increase = min(0.05, (target_profit / 100))
        recommended_price = current_price * (1 + price_increase)
        price_change_pct = price_increase * 100
        recommendation_type = "increase"
        factors.append("increase price to improve margins")
    
    # Factor 2: Inventory pressure
    if inventory_ratio > 2.0:
        # High inventory - consider discount to clear
        discount = min(0.08, state["max_discount"])
        new_price = current_price * (1 - discount)
        if new_price < recommended_price or recommendation_type == "maintain":
            recommended_price = new_price
            price_change_pct = -discount * 100
            recommendation_type = "clearance"
            factors.append("discount to clear excess inventory")
    elif inventory_ratio < 0.5:
        # Low inventory - can increase price
        increase = min(0.05, (target_profit / 100) if target_profit > 0 else 0.03)
        new_price = current_price * (1 + increase)
        if new_price > recommended_price:
            recommended_price = new_price
            price_change_pct = increase * 100
            recommendation_type = "premium"
            factors.append("premium pricing due to low stock")
    
    # Factor 3: Target profit optimization
    if target_profit > 0 and recommendation_type == "maintain":
        # Try to optimize for profit target
        current_margin = base_margin
        required_margin = (target_profit / 100) + min_margin
        if required_margin > current_margin:
            # Need to increase price
            margin_gap = required_margin - current_margin
            price_increase = margin_gap / (1 - required_margin)
            price_increase = min(price_increase, 0.10)  # Cap at 10%
            recommended_price = current_price * (1 + price_increase)
            price_change_pct = price_increase * 100
            recommendation_type = "optimize"
            factors.append(f"optimize price to meet {target_profit}% profit target")
    
    # Ensure we don't go below minimum margin
    cost = current_price * (1 - base_margin)
    min_price = cost / (1 - min_margin)
    if recommended_price < min_price:
        recommended_price = min_price
        price_change_pct = ((recommended_price - current_price) / current_price) * 100
        recommendation_type = "floor"
        factors.append("price adjusted to maintain minimum margin")
    
    # Calculate expected impacts
    price_change_decimal = price_change_pct / 100
    expected_demand_change = elasticity * price_change_decimal
    new_demand = forecasted_demand * (1 + expected_demand_change)
    
    current_revenue = current_price * forecasted_demand
    new_revenue = recommended_price * new_demand
    expected_revenue_change = ((new_revenue - current_revenue) / current_revenue) * 100 if current_revenue > 0 else 0
    
    current_profit = current_price * forecasted_demand * base_margin
    new_margin = 1 - (cost / recommended_price) if recommended_price > 0 else base_margin
    new_profit = recommended_price * new_demand * new_margin
    expected_profit_change = ((new_profit - current_profit) / current_profit) * 100 if current_profit > 0 else 0
    
    state["recommended_price"] = round(recommended_price, 2)
    state["price_change_pct"] = round(price_change_pct, 2)
    state["expected_demand_change"] = round(expected_demand_change * 100, 1)
    state["expected_revenue_change"] = round(expected_revenue_change, 1)
    state["expected_profit_change"] = round(expected_profit_change, 1)
    state["recommendation_type"] = recommendation_type
    
    if factors:
        state["explanation_factors"].extend(factors)
    
    return state


def narrative_node(state: PricingState):
    """Generate AI narrative for the pricing recommendation"""
    if client is None:
        state["narrative"] = (
            f"Recommended {state['recommendation_type']} pricing strategy. "
            f"Price change: {state['price_change_pct']:.1f}%. "
            f"Expected profit impact: {state['expected_profit_change']:.1f}%."
        )
        return state

    prompt = f"""
You are a retail pricing strategist.

Category: {state['category']}
Current Price: ₹{state['current_price']:.2f}
Recommended Price: ₹{state['recommended_price']:.2f}
Price Change: {state['price_change_pct']:.1f}%
Recommendation Type: {state['recommendation_type']}

Expected Impact:
- Demand Change: {state['expected_demand_change']:.1f}%
- Revenue Change: {state['expected_revenue_change']:.1f}%
- Profit Change: {state['expected_profit_change']:.1f}%

Key Factors:
{', '.join(state['explanation_factors'])}

Explain the pricing recommendation in clear, store-manager friendly language.
Keep it concise (2-3 sentences) and actionable.
"""

    try:
        res = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        state["narrative"] = res.choices[0].message.content
    except Exception as e:
        log(f"Narrative generation error: {e}")
        state["narrative"] = (
            f"Recommended {state['recommendation_type']} pricing strategy. "
            f"Price change: {state['price_change_pct']:.1f}%. "
            f"Expected profit impact: {state['expected_profit_change']:.1f}%."
        )

    return state

# -------------------------------------------------
# Build Graph
# -------------------------------------------------
graph = StateGraph(PricingState)

graph.add_node("load_data", load_category_data_node)
graph.add_node("competitor_analysis", analyze_competitor_position_node)
graph.add_node("elasticity_analysis", calculate_elasticity_impact_node)
graph.add_node("inventory_analysis", inventory_pressure_node)
graph.add_node("pricing_decision", pricing_decision_node)
graph.add_node("narrative", narrative_node)

graph.set_entry_point("load_data")

graph.add_edge("load_data", "competitor_analysis")
graph.add_edge("competitor_analysis", "elasticity_analysis")
graph.add_edge("elasticity_analysis", "inventory_analysis")
graph.add_edge("inventory_analysis", "pricing_decision")
graph.add_edge("pricing_decision", "narrative")

pricing_graph = graph.compile()

log(">>> LangGraph compiled successfully")

# -------------------------------------------------
# MCP Tool
# -------------------------------------------------
@mcp.tool()
async def getPricingStrategy(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a pricing strategy recommendation using reasoning graph.
    
    Input should contain:
    - category: str (product category)
    - current_price: float (current selling price)
    - forecasted_demand: float (expected demand from forecasting server)
    - inventory_level: float (current inventory units)
    - target_profit_pct: float (optional, target profit percentage)
    """
    log(">>> MCP Tool called: getPricingStrategy")
    
    result = pricing_graph.invoke({"input": input})
    
    return {
        "category": result["category"],
        "current_price": result["current_price"],
        "recommended_price": result["recommended_price"],
        "price_change_pct": result["price_change_pct"],
        "recommendation_type": result["recommendation_type"],
        "expected_demand_change": result["expected_demand_change"],
        "expected_revenue_change": result["expected_revenue_change"],
        "expected_profit_change": result["expected_profit_change"],
        "narrative": result["narrative"],
        "explanation_factors": result["explanation_factors"]
    }

# -------------------------------------------------
# Run MCP Server
# -------------------------------------------------
if __name__ == "__main__":
    log(">>> Starting Pricing Strategy MCP Server (STDIO)")
    mcp.run()

