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
    print(f"[MOCK-REPLENISHMENT] {msg}", file=sys.stderr, flush=True)

mcp = FastMCP("mock-replenishment-server")
baseline = TightlyCoupledRetailOps()

@mcp.tool()
async def getReplenishmentDecision(input: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic replenishment decision matching baseline domain formulas."""
    # Check for test-only fault injection directly
    try:
        import tempfile
        import json
        sig_file = Path(tempfile.gettempdir()) / "retailops_fault_signal.json"
        fault = None
        if sig_file.exists():
            with open(sig_file, "r", encoding="utf-8") as sf:
                data = json.load(sf)
                if data.get("service", "").lower() in ["replenishment", "all"]:
                    fault = data
        if not fault:
            target = os.getenv("RETAILOPS_FAILURE_SERVICE", "").lower()
            if target in ["replenishment", "all"]:
                fault = {
                    "mode": os.getenv("RETAILOPS_FAILURE_MODE", "tool_error"),
                    "message": os.getenv("RETAILOPS_FAILURE_MESSAGE", "Injected deterministic error in Replenishment Decision")
                }
        if fault:
            mode = fault.get("mode", "tool_error")
            msg = fault.get("message", "Injected deterministic error in Replenishment Decision")
            if mode == "crash_exit":
                log(f">>> [FAULT INJECTION] Crashing replenishment process immediately: {msg}")
                os._exit(1)
            elif mode == "invalid_response":
                return {"corrupt": True}
            else:
                return {"error": msg}
    except Exception as e:
        log(f">>> Fault check exception: {e}")

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
