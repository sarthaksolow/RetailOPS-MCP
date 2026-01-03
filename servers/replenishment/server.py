import os
import sys
from typing import TypedDict, Dict, Any, List

from mcp.server.fastmcp import FastMCP
from langgraph.graph import StateGraph
from openai import OpenAI

# -------------------------------------------------
# STDIO-safe logging (IMPORTANT)
# -------------------------------------------------
def log(msg: str):
    print(msg, file=sys.stderr, flush=True)

log(">>> Loading Replenishment MCP Server")

# -------------------------------------------------
# OpenRouter Client (FREE API)
# -------------------------------------------------
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "http://localhost",
        "X-Title": "Replenishment Reasoning Engine"
    }
)

# -------------------------------------------------
# MCP Init
# -------------------------------------------------
mcp = FastMCP("replenishment-server")

# -------------------------------------------------
# LangGraph State
# -------------------------------------------------
class ReplenishmentState(TypedDict):
    input: Dict[str, Any]

    volatility_multiplier: float
    festival_multiplier: float
    effective_stock: int
    stock_runway_days: float
    safety_stock: float

    reorder_qty: int
    reorder_timing: str
    stockout_risk: str
    explanation_factors: List[str]
    narrative: str

# -------------------------------------------------
# Graph Nodes
# -------------------------------------------------
def demand_risk_node(state: ReplenishmentState):
    volatility = state["input"]["forecast"]["demand_volatility"]
    multiplier_map = {"low": 1.1, "medium": 1.25, "high": 1.4}

    state["volatility_multiplier"] = multiplier_map[volatility]
    state["explanation_factors"] = [f"demand volatility is {volatility}"]
    return state


def festival_urgency_node(state: ReplenishmentState):
    event = state["input"]["forecast"]["event"]
    lead_time = state["input"]["supplier"]["lead_time_days"]

    if event["days_to_event"] is not None and event["days_to_event"] <= lead_time:
        state["festival_multiplier"] = 1.2
        state["explanation_factors"].append(
            f"festival ({event['name']}) is within supplier lead time"
        )
    else:
        state["festival_multiplier"] = 1.0

    return state


def inventory_runway_node(state: ReplenishmentState):
    inv = state["input"]["inventory"]
    avg_daily = state["input"]["forecast"]["avg_daily_demand"]

    effective_stock = inv["current_stock"] + inv["in_transit_stock"]
    runway_days = effective_stock / avg_daily

    state["effective_stock"] = effective_stock
    state["stock_runway_days"] = round(runway_days, 1)
    return state


def safety_stock_node(state: ReplenishmentState):
    avg_daily = state["input"]["forecast"]["avg_daily_demand"]
    lead_time = state["input"]["supplier"]["lead_time_days"]

    base = avg_daily * lead_time
    state["safety_stock"] = round(
        base * state["volatility_multiplier"] * state["festival_multiplier"]
    )
    return state


def reorder_decision_node(state: ReplenishmentState):
    demand = state["input"]["forecast"]["forecasted_demand"]
    effective_stock = state["effective_stock"]
    moq = state["input"]["supplier"]["minimum_order_quantity"]

    raw_qty = max(0, int(demand + state["safety_stock"] - effective_stock))
    if raw_qty > 0:
        raw_qty = max(raw_qty, moq)

    state["reorder_qty"] = raw_qty
    return state


def timing_risk_node(state: ReplenishmentState):
    lead_time = state["input"]["supplier"]["lead_time_days"]
    runway = state["stock_runway_days"]

    if runway < lead_time:
        state["reorder_timing"] = "immediate"
        state["stockout_risk"] = "high"
    elif runway < 30:
        state["reorder_timing"] = "soon"
        state["stockout_risk"] = "medium"
    else:
        state["reorder_timing"] = "defer"
        state["stockout_risk"] = "low"

    state["explanation_factors"].append(
        f"stock runway is {state['stock_runway_days']} days"
    )
    return state


def narrative_node(state: ReplenishmentState):
    prompt = f"""
You are a retail supply chain expert.

Decision:
- Reorder Quantity: {state['reorder_qty']}
- Timing: {state['reorder_timing']}
- Stockout Risk: {state['stockout_risk']}

Reasoning factors:
{', '.join(state['explanation_factors'])}

Explain the replenishment decision in clear, store-manager friendly language.
Keep it concise (2–3 sentences).
"""

    try:
        res = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120
        )
        state["narrative"] = res.choices[0].message.content
    except Exception:
        state["narrative"] = (
            "Replenishment decision based on demand risk, "
            "festival proximity, and inventory runway."
        )

    return state

# -------------------------------------------------
# Build Graph
# -------------------------------------------------
graph = StateGraph(ReplenishmentState)

graph.add_node("demand_risk", demand_risk_node)
graph.add_node("festival", festival_urgency_node)
graph.add_node("inventory", inventory_runway_node)
graph.add_node("safety", safety_stock_node)
graph.add_node("reorder", reorder_decision_node)
graph.add_node("timing", timing_risk_node)
graph.add_node("narrative", narrative_node)

graph.set_entry_point("demand_risk")

graph.add_edge("demand_risk", "festival")
graph.add_edge("festival", "inventory")
graph.add_edge("inventory", "safety")
graph.add_edge("safety", "reorder")
graph.add_edge("reorder", "timing")
graph.add_edge("timing", "narrative")

replenishment_graph = graph.compile()

log(">>> LangGraph compiled successfully")

# -------------------------------------------------
# MCP Tool
# -------------------------------------------------
@mcp.tool()
async def getReplenishmentDecision(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a replenishment decision using reasoning graph.
    """
    log(">>> MCP Tool called: getReplenishmentDecision")

    result = replenishment_graph.invoke({"input": input})

    return {
        "reorder_qty": result["reorder_qty"],
        "reorder_timing": result["reorder_timing"],
        "stockout_risk": result["stockout_risk"],
        "narrative": result["narrative"]
    }

# -------------------------------------------------
# Run MCP Server
# -------------------------------------------------
if __name__ == "__main__":
    log(">>> Starting Replenishment MCP Server (STDIO)")
    mcp.run()
