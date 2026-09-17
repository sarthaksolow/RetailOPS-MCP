"""
Deterministic Replacement Forecasting Service for Tightly Coupled Baseline.
Computes a 60-day moving average (instead of 30-day) with identical schema contract.
Maintains pure function isolation separate from the original baseline implementation.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd


def replacement_direct_get_forecast(
    category: str,
    days_ahead: int = 30,
    sales_df: Optional[pd.DataFrame] = None,
    events: Optional[Dict[str, Any]] = None,
    surge_profiles: Optional[Dict[str, Any]] = None,
    moving_average_window: int = 60
) -> Dict[str, Any]:
    """
    Direct in-process replacement forecasting function.
    Preserves exact input and output contract required by replenishment and pricing.
    Uses 60-day moving average window deterministically.
    """
    if sales_df is None or sales_df.empty:
        return {"error": "Sales data unavailable."}

    filtered = sales_df[sales_df["category"] == category]
    if filtered.empty:
        return {"error": f"No data found for category '{category}'."}

    # 60-day moving average
    last_days = filtered.tail(moving_average_window)
    base = round(float(last_days["sales"].mean()), 2)

    # Seasonal events
    today = datetime.now()
    event_name = None
    season_mult = 1.0
    events_list = (events or {}).get("events", [])
    for e in events_list:
        try:
            event_date = datetime.strptime(e["date"], "%Y-%m-%d")
            days_until = (event_date - today).days
            if 0 <= days_until <= 180:
                event_name = e["name"]
                season_mult = float(e["multiplier"])
                break
        except Exception:
            continue

    # Historical surge factor
    hist_mult = 1.0
    if event_name and surge_profiles and event_name in surge_profiles:
        hist_mult = float(surge_profiles[event_name].get(category, 1.0))

    final_forecast = round(base * season_mult * hist_mult, 2)
    narrative = (
        f"Deterministic Replacement Forecast (60-day MA): Base {base} adjusted by "
        f"seasonal factor {season_mult}x and event surge {hist_mult}x for event '{event_name or 'None'}'."
    )

    return {
        "category": category,
        "base_forecast": base,
        "seasonal_multiplier": season_mult,
        "historical_surge_factor": hist_mult,
        "final_forecast": final_forecast,
        "event": event_name,
        "narrative": narrative
    }
