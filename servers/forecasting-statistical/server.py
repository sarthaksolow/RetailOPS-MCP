"""
Statistical Replacement Forecasting MCP Server for RetailOps.
Implements Holt-Winters Triple Exponential Smoothing with weekly seasonality.
Exposes the standard FastMCP tool: getForecast.

Preserves exact input and output schema contracts required by downstream stages.
Operates completely offline without external LLM dependencies for numerical prediction.
Prevents data leakage by training only on pre-test historical data.
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from mcp.server.fastmcp import FastMCP

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Redirect logging to stderr so it does not interfere with MCP STDIO transport
def log(msg: str):
    print(f"[FORECASTING-STATISTICAL] {msg}", file=sys.stderr, flush=True)

log(">>> Loading Statistical Forecasting MCP Server (Holt-Winters Exponential Smoothing)")

mcp = FastMCP("forecasting-statistical-server")

# Load shared datasets from standard forecasting data directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "forecasting", "data"))

sales_path = os.path.join(DATA_DIR, "sales_history.csv")
events_path = os.path.join(DATA_DIR, "events.json")
surge_path = os.path.join(DATA_DIR, "surge_profile.json")

try:
    sales_df = pd.read_csv(sales_path)
    log(f">>> Sales loaded: {len(sales_df)} rows")
    with open(events_path, "r", encoding="utf-8") as f:
        events = json.load(f)
    with open(surge_path, "r", encoding="utf-8") as f:
        surge_profiles = json.load(f)
except Exception as e:
    log(f"⚠️ Error loading forecasting data: {e}")
    raise SystemExit(1)


# =====================================================================
# HOLT-WINTERS TRIPLE EXPONENTIAL SMOOTHING ALGORITHM
# =====================================================================
def fit_predict_holt_winters(
    series: np.ndarray,
    season_length: int = 7,
    n_preds: int = 30,
    alpha: float = 0.25,
    beta: float = 0.05,
    gamma: float = 0.20
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Fits an additive Holt-Winters model to historical series and forecasts n_preds steps ahead.
    All parameters are fit strictly on the provided series without lookahead.
    
    Parameters:
      series: 1D array of historical demand (training split)
      season_length: Periodicity (7 days for weekly retail cycle)
      n_preds: Horizon steps to predict
      alpha: Level smoothing factor [0, 1]
      beta: Trend smoothing factor [0, 1]
      gamma: Seasonal smoothing factor [0, 1]
    
    Returns:
      predictions: Array of length n_preds with forecasted values
      metadata: Fitting and parameter metadata dictionary
    """
    n = len(series)
    if n < 2 * season_length:
        # Fallback to simple mean if series is too short
        mean_val = float(np.mean(series))
        return np.full(n_preds, mean_val), {"model": "fallback_mean", "n_samples": n}
    
    # 1. Initialize level
    level = float(series[0])
    
    # 2. Initialize trend (mean slope across first season)
    trend = float(np.mean([
        series[i + season_length] - series[i]
        for i in range(min(season_length, n - season_length))
    ]) / season_length)
    
    # 3. Initialize seasonal indices
    seasons = [float(series[i] - level) for i in range(season_length)]
    
    # 4. Forward smoothing pass over historical training data
    for i in range(n):
        val = float(series[i])
        s_idx = i % season_length
        last_level = level
        last_trend = trend
        last_season = seasons[s_idx]
        
        # Level update
        level = alpha * (val - last_season) + (1.0 - alpha) * (last_level + last_trend)
        # Trend update
        trend = beta * (level - last_level) + (1.0 - beta) * last_trend
        # Seasonal update
        seasons[s_idx] = gamma * (val - level) + (1.0 - gamma) * last_season
        
    # 5. Out-of-sample forecast generation
    preds = []
    for m in range(1, n_preds + 1):
        s_idx = (n + m - 1) % season_length
        pred = level + m * trend + seasons[s_idx]
        preds.append(max(0.0, float(pred)))
        
    metadata = {
        "model_type": "holt_winters_additive",
        "season_length": season_length,
        "alpha": alpha,
        "beta": beta,
        "gamma": gamma,
        "final_level": round(level, 4),
        "final_trend": round(trend, 4),
        "training_samples": n
    }
    return np.array(preds), metadata


def get_season_multiplier() -> Tuple[Optional[str], float]:
    """Get seasonal multiplier based on upcoming calendar events (within 180 days)."""
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


def get_historical_surge(category: str, event_name: Optional[str]) -> float:
    """Get historical surge factor for category during specific event."""
    if event_name and event_name in surge_profiles:
        return float(surge_profiles[event_name].get(category, 1.0))
    return 1.0


# =====================================================================
# FASTMCP TOOL INTERFACE
# =====================================================================
@mcp.tool()
async def getForecast(category: str, days_ahead: int = 30) -> dict:
    """
    Generate demand forecast for a product category using Holt-Winters Exponential Smoothing.
    Preserves exact input and output schema contracts required by RetailOps.
    """
    log(f">>> getForecast called for category='{category}', days_ahead={days_ahead}")
    
    # Fault injection hook for reliability and governance tests
    try:
        from experiments.fault_tolerance.failure_scenarios import should_inject_fault
        fault = should_inject_fault("forecasting")
        if fault:
            mode = fault.get("mode", "tool_error")
            msg = fault.get("message", "Injected deterministic fault in Statistical Forecasting")
            if mode == "crash_exit":
                log(f">>> [FAULT INJECTION] Crashing process: {msg}")
                os._exit(1)
            elif mode == "invalid_response":
                return {"corrupt": True}
            else:
                return {"error": msg}
    except ImportError:
        pass

    # Extract historical training series for category
    filtered = sales_df[sales_df["category"] == category].sort_values("date").reset_index(drop=True)
    if filtered.empty:
        return {"error": f"No data found for category '{category}'."}

    # Data leakage protection: Use first 92 days (training boundary) if evaluated against protocol split,
    # or all historical data if running in live operation without split.
    # To be strictly aligned with the frozen protocol, we reserve the last 30 observations for out-of-sample test.
    if len(filtered) > 30:
        train_series = filtered.iloc[:-30]["sales"].values.astype(float)
    else:
        train_series = filtered["sales"].values.astype(float)

    horizon = int(days_ahead) if days_ahead else 30
    
    # Generate Holt-Winters forecasts
    predictions, metadata = fit_predict_holt_winters(
        train_series,
        season_length=7,
        n_preds=horizon,
        alpha=0.25,
        beta=0.05,
        gamma=0.20
    )
    
    # Base forecast is the daily expected rate from the model
    base_forecast = round(float(np.mean(predictions)), 2)
    
    event_name, season_mult = get_season_multiplier()
    hist_mult = get_historical_surge(category, event_name)
    
    # Event-adjusted final forecast
    final_forecast = round(base_forecast * season_mult * hist_mult, 2)
    
    narrative = (
        f"Statistical Replacement Forecast (Holt-Winters Exponential Smoothing): "
        f"Modeled weekly seasonality (period=7) over {len(train_series)} training days. "
        f"Base daily forecast: {base_forecast} units/day. "
        f"Event adjustment ({event_name or 'None'}): seasonal factor {season_mult}x, "
        f"historical surge {hist_mult}x -> final forecast {final_forecast} units/day."
    )
    
    result = {
        "category": category,
        "base_forecast": base_forecast,
        "seasonal_multiplier": season_mult,
        "historical_surge_factor": hist_mult,
        "final_forecast": final_forecast,
        "event": event_name,
        "narrative": narrative,
        "model_metadata": metadata
    }
    
    log(f">>> Statistical forecast generated: base={base_forecast}, final={final_forecast}")
    return result


if __name__ == "__main__":
    log(">>> Starting Statistical Forecasting MCP Server in STDIO mode")
    mcp.run()
