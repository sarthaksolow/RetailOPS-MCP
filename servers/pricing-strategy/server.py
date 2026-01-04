import os
import sys
import json
from typing import TypedDict, Dict, Any, List

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from langgraph.graph import StateGraph
from openai import OpenAI

# =====================================================
# ENV + STDIO SAFE LOGGING
# =====================================================
load_dotenv()

def log(msg: str):
    # IMPORTANT: never print to stdout in MCP servers
    print(msg, file=sys.stderr, flush=True)

log(">>> Loading Pricing Strategy MCP Server")

# =====================================================
# OpenRouter Client
# =====================================================
api_key = os.getenv("OPENROUTER_API_KEY")

client = None
if api_key:
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "http://localhost",
            "X-Title": "RetailOPS Pricing Strategy"
        }
    )
    log(">>> OpenRouter configured")
else:
    log("⚠️ OPENROUTER_API_KEY not found – running fallback mode")

# =====================================================
# MCP INIT
# =====================================================
mcp = FastMCP("pricing-strategy-server")

# =====================================================
# LOAD DATA
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

with open(os.path.join(DATA_DIR, "price_elasticity.json")) as f:
    elasticity_data = json.load(f)

with open(os.path.join(DATA_DIR, "competitor_prices.json")) as f:
    competitor_data = json.load(f)

log(">>> Pricing datasets loaded")

# =====================================================
# STATE
# =====================================================
class PricingState(TypedDict):
    input: Dict[str, Any]

    category: str
    current_price: float
    forecasted_demand: float
    inventory_level: float
    target_profit_pct: float

    elasticity: float
    competitor_price: float
    inventory_ratio: float

    recommended_price: float
    price_change_pct: float
    recommendation_type: str
    explanation_factors: List[str]
    narrative: str

# =====================================================
# GRAPH NODES
# =====================================================
def load_inputs(state: PricingState):
    i = state["input"]
    cat = i["category"]

    state["category"] = cat
    state["current_price"] = i["current_price"]
    state["forecasted_demand"] = i["forecasted_demand"]
    state["inventory_level"] = i["inventory_level"]
    state["target_profit_pct"] = i.get("target_profit_pct", 0)

    state["elasticity"] = elasticity_data.get(cat, {}).get("elasticity", -1.5)
    state["competitor_price"] = competitor_data.get(cat, {}).get(
        "competitor_avg_price",
        state["current_price"]
    )

    state["inventory_ratio"] = (
        state["inventory_level"] / max(1, state["forecasted_demand"])
    )

    state["explanation_factors"] = []
    return state


def pricing_logic(state: PricingState):
    price = state["current_price"]
    inv_ratio = state["inventory_ratio"]
    competitor = state["competitor_price"]

    new_price = price
    rec_type = "maintain"

    if inv_ratio > 2:
        new_price = price * 0.92
        rec_type = "clearance"
        state["explanation_factors"].append("excess inventory")
    elif inv_ratio < 0.5:
        new_price = price * 1.05
        rec_type = "premium"
        state["explanation_factors"].append("low inventory")
    elif price > competitor * 1.1:
        new_price = price * 0.95
        rec_type = "competitive"
        state["explanation_factors"].append("above competitor pricing")

    state["recommended_price"] = round(new_price, 2)
    state["price_change_pct"] = round(((new_price - price) / price) * 100, 2)
    state["recommendation_type"] = rec_type

    return state


def narrative_node(state: PricingState):
    if not client:
        state["narrative"] = (
            f"{state['recommendation_type']} pricing recommended "
            f"({state['price_change_pct']}% change)."
        )
        return state

    prompt = f"""
You are a retail pricing expert.

Category: {state['category']}
Current Price: ₹{state['current_price']}
Recommended Price: ₹{state['recommended_price']}
Reason: {', '.join(state['explanation_factors'])}

Explain this pricing decision clearly in 2 sentences.
"""

    try:
        res = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120
        )
        state["narrative"] = res.choices[0].message.content
    except Exception:
        state["narrative"] = "Pricing adjusted based on inventory and competition."

    return state

# =====================================================
# BUILD GRAPH
# =====================================================
graph = StateGraph(PricingState)
graph.add_node("load", load_inputs)
graph.add_node("logic", pricing_logic)
graph.add_node("narrative", narrative_node)

graph.set_entry_point("load")
graph.add_edge("load", "logic")
graph.add_edge("logic", "narrative")

pricing_graph = graph.compile()
log(">>> Pricing LangGraph compiled")

# =====================================================
# MCP TOOL
# =====================================================
@mcp.tool()
async def getPricingStrategy(input: Dict[str, Any]) -> Dict[str, Any]:
    result = pricing_graph.invoke({"input": input})
    return {
        "category": result["category"],
        "current_price": result["current_price"],
        "recommended_price": result["recommended_price"],
        "price_change_pct": result["price_change_pct"],
        "recommendation_type": result["recommendation_type"],
        "narrative": result["narrative"]
    }

# =====================================================
# RUN
# =====================================================
if __name__ == "__main__":
    log(">>> Starting Pricing Strategy MCP Server (STDIO)")
    mcp.run()