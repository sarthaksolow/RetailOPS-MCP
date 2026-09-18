import json
import pandas as pd
from datetime import datetime
from mcp.server.fastmcp import FastMCP
import os
import sys

# Redirect prints to stderr so they don't interfere with STDIO JSON communication
def log(message):
    print(f"[REPLACEMENT-FORECAST] {message}", file=sys.stderr, flush=True)

log(">>> Loading Replacement Forecasting MCP Server (60-day MA & Seasonal)")

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Initialize MCP server with clear experimental identifier
mcp = FastMCP("replacement-forecasting-server")

# Load data safely from shared forecasting data directory
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    log(f"BASE_DIR: {BASE_DIR}")

    # Reference the standard forecasting data directory
    data_dir = os.path.abspath(os.path.join(BASE_DIR, "..", "forecasting", "data"))
    sales_path = os.path.join(data_dir, "sales_history.csv")
    events_path = os.path.join(data_dir, "events.json")
    surge_path = os.path.join(data_dir, "surge_profile.json")

    log(f"Sales path: {sales_path}")
    log(f"Events path: {events_path}")
    log(f"Surge path: {surge_path}")

    sales_df = pd.read_csv(sales_path)
    log(f">>> Sales loaded: {len(sales_df)} rows")

    with open(events_path, "r", encoding="utf-8") as f:
        events = json.load(f)
    log(f">>> Events loaded: {len(events.get('events', []))} events")

    with open(surge_path, "r", encoding="utf-8") as f:
        surge_profiles = json.load(f)
    log(f">>> Surge profiles loaded: {len(surge_profiles)} profiles")

except Exception as e:
    log(f"Startup error loading files: {e}")
    import traceback
    traceback.print_exc(file=sys.stderr)
    raise SystemExit(1)


def extended_moving_average(category: str, days: int = 60):
    """
    Deterministic replacement calculation:
    Calculates 60-day simple moving average (instead of 30-day).
    """
    filtered = sales_df[sales_df["category"] == category]
    if filtered.empty:
        return None

    last_days = filtered.tail(days)
    return round(float(last_days["sales"].mean()), 2)


def get_season_multiplier():
    """Get seasonal multiplier based on upcoming events (within 6 months)"""
    today = datetime.now()
    for e in events.get("events", []):
        try:
            event_date = datetime.strptime(e["date"], "%Y-%m-%d")
            days_until = (event_date - today).days
            if 0 <= days_until <= 180:
                return e["name"], float(e["multiplier"])
        except Exception:
            continue
    return None, 1.0


def get_historical_surge(category: str, event_name: str):
    """Get historical surge factor for a category during specific event"""
    if event_name and event_name in surge_profiles:
        return float(surge_profiles[event_name].get(category, 1.0))
    return 1.0


@mcp.tool()
async def getForecast(category: str, days_ahead: int = 30) -> dict:
    """
    Generate a sales forecast for a product category using the replacement 60-day window.
    Preserves exact input and output schema contracts required by downstream stages.
    """
    log(f">>> replacement getForecast called for category: {category}, days_ahead requested: {days_ahead}")

    # Check for test-only fault injection
    try:
        from experiments.fault_tolerance.failure_scenarios import should_inject_fault
        fault = should_inject_fault("forecasting")
        if fault:
            mode = fault.get("mode", "tool_error")
            msg = fault.get("message", "Injected deterministic error in Forecasting")
            if mode == "crash_exit":
                log(f">>> [FAULT INJECTION] Crashing forecasting process immediately: {msg}")
                os._exit(1)
            elif mode == "invalid_response":
                return {"corrupt": True}
            else:
                return {"error": msg}
    except ImportError:
        pass

    # Use 60-day moving average window as deterministic alternative algorithm
    base = extended_moving_average(category, days=60)
    if base is None:
        return {"error": f"No data found for category '{category}'."}

    event_name, season_mult = get_season_multiplier()
    hist_mult = get_historical_surge(category, event_name)

    final_forecast = round(base * season_mult * hist_mult, 2)

    narrative = (
        f"Deterministic Replacement Forecast (60-day MA): Base {base} units/day adjusted by "
        f"seasonal factor {season_mult}x and event surge {hist_mult}x for event '{event_name or 'None'}'."
    )

    result = {
        "category": category,
        "base_forecast": base,
        "seasonal_multiplier": season_mult,
        "historical_surge_factor": hist_mult,
        "final_forecast": final_forecast,
        "event": event_name,
        "narrative": narrative
    }

    log(">>> Replacement forecast generated successfully")
    return result


log(">>> Replacement Forecasting MCP Server loaded successfully")

if __name__ == "__main__":
    log(">>> Starting Replacement MCP server in STDIO mode")
    mcp.run()
