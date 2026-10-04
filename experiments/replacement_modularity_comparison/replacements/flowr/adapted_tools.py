"""
Flowr Coordinator Adapter: Statistical Forecasting Tool Replacement.
Extends FlowrDomainTools to override demand projection with Holt-Winters model.
"""
from typing import Dict, Any
from experiments.m5_operational.decision_provider import OperationalDecisionContext
from experiments.same_repo_comparison.flowr_coordinator.coordinator import FlowrDomainTools
from experiments.replacement_modularity_comparison.statistical_model import compute_statistical_demand


class FlowrStatisticalDomainTools(FlowrDomainTools):
    """
    Subclass adapter overriding the demand forecasting domain function
    with statistical triple exponential smoothing.
    """

    @staticmethod
    def forecast_demand(context: OperationalDecisionContext) -> Dict[str, Any]:
        """Replacement domain tool: Holt-Winters statistical forecasting."""
        daily_d = context.mean_historical_daily_demand
        L = context.supplier_lead_time_days

        stat_res = compute_statistical_demand(
            mean_daily=daily_d,
            lead_time_days=L,
            event_name=context.event_name
        )

        return {
            "mean_daily": daily_d,
            "horizon_days": L,
            "event_surge_factor": stat_res["event_multiplier"],
            "projected_lead_time_demand": stat_res["projected_lead_time_demand"],
            "model_metadata": stat_res["model_metadata"]
        }
