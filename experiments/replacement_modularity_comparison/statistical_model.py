"""
Statistical Forecasting Engine for Cross-Architecture Replacement Experiment.
Implements Holt-Winters Triple Exponential Smoothing with weekly seasonality.
Shared across all four architectural replacements to ensure algorithmic parity.
"""
from typing import Dict, Any, Tuple
import numpy as np


def fit_predict_holt_winters(
    series: np.ndarray,
    season_length: int = 7,
    n_preds: int = 7,
    alpha: float = 0.25,
    beta: float = 0.05,
    gamma: float = 0.20
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Fits an additive Holt-Winters model to historical series and forecasts n_preds steps ahead.
    All parameters are fit strictly on the provided series without lookahead.
    """
    n = len(series)
    if n < 2 * season_length:
        mean_val = float(np.mean(series)) if n > 0 else 1.0
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


def compute_statistical_demand(
    mean_daily: float,
    lead_time_days: int,
    event_name: str = None,
    series_history: np.ndarray = None
) -> Dict[str, Any]:
    """
    Standardized forecast evaluation helper for decision context.
    Computes lead-time demand projection using Holt-Winters smoothing.
    """
    horizon = max(1, int(lead_time_days))
    event_mult = 1.2 if (event_name and str(event_name).strip()) else 1.0

    if series_history is not None and len(series_history) >= 14:
        preds, meta = fit_predict_holt_winters(series_history, season_length=7, n_preds=horizon)
        projected = float(np.sum(preds)) * event_mult
    else:
        # Synthetic 28-day baseline series matching mean_daily with minor weekly seasonality
        base_week = np.array([0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 0.85]) * mean_daily
        synthetic_history = np.tile(base_week, 4)
        preds, meta = fit_predict_holt_winters(synthetic_history, season_length=7, n_preds=horizon)
        projected = float(np.sum(preds)) * event_mult

    return {
        "projected_lead_time_demand": round(projected, 2),
        "horizon_days": horizon,
        "event_multiplier": event_mult,
        "model_metadata": meta
    }
