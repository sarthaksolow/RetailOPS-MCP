import sys
import os
from typing import Dict, Any
from pathlib import Path
from mcp.server.fastmcp import FastMCP

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from baseline.tightly_coupled import TightlyCoupledRetailOps

def log(msg: str):
    print(f"[MOCK-PRICING] {msg}", file=sys.stderr, flush=True)

mcp = FastMCP("mock-pricing-server")
baseline = TightlyCoupledRetailOps()

@mcp.tool()
async def getPricingStrategy(input: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic pricing strategy matching baseline domain formulas."""
    # Check for test-only fault injection
    try:
        from experiments.fault_tolerance.failure_scenarios import should_inject_fault
        fault = should_inject_fault("pricing")
        if fault:
            mode = fault.get("mode", "tool_error")
            msg = fault.get("message", "Injected deterministic error in Pricing Strategy")
            if mode == "crash_exit":
                log(f">>> [FAULT INJECTION] Crashing pricing process immediately: {msg}")
                os._exit(1)
            elif mode == "invalid_response":
                return {"corrupt": True}
            else:
                return {"error": msg}
    except ImportError:
        pass

    category = input.get("category", "general")
    forecasted_demand = input.get("forecasted_demand", 0)
    inventory_level = input.get("inventory_level", 100)
    current_price = input.get("current_price", 1000)
    res = baseline.direct_get_pricing(
        category=category,
        forecasted_demand=forecasted_demand,
        current_price=current_price,
        inventory_level=inventory_level
    )
    return res

if __name__ == "__main__":
    log(">>> Starting Mock Deterministic Pricing (STDIO)")
    mcp.run()
