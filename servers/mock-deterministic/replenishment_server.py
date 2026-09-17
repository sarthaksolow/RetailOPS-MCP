import sys
import os
from typing import Dict, Any
from pathlib import Path
from mcp.server.fastmcp import FastMCP

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from baseline.tightly_coupled import TightlyCoupledRetailOps

def log(msg: str):
    print(f"[MOCK-REPLENISHMENT] {msg}", file=sys.stderr, flush=True)

mcp = FastMCP("mock-replenishment-server")
baseline = TightlyCoupledRetailOps()

@mcp.tool()
async def getReplenishmentDecision(input: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic replenishment decision matching baseline domain formulas."""
    forecast_data = {
        "category": input.get("category"),
        "final_forecast": input.get("forecast", {}).get("forecasted_demand"),
        "event": input.get("forecast", {}).get("event", {}).get("name")
    }
    current_stock = input.get("inventory", {}).get("current_stock")
    in_transit = input.get("inventory", {}).get("in_transit_stock")
    res = baseline.direct_get_replenishment(forecast_data, current_stock, in_transit)
    return res

if __name__ == "__main__":
    log(">>> Starting Mock Deterministic Replenishment (STDIO)")
    mcp.run()
