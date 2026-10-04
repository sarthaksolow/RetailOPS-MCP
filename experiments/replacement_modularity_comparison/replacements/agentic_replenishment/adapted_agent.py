"""
Agentic Replenishment Adapter: Statistical Forecasting Replacement.
Demonstrates replacement effort under the Direct Autonomous Replenishment pattern.
Because the baseline couples perception, forecasting, and constraint handling in a single
unbundled loop, replacing the demand model requires overriding/duplicating the entire decide() loop.
"""
from experiments.m5_operational.decision_provider import (
    BaseDecisionProvider,
    OperationalDecisionContext,
    ReplenishmentDecision
)
from experiments.replacement_modularity_comparison.statistical_model import compute_statistical_demand


class AgenticStatisticalReplacementProvider(BaseDecisionProvider):
    """
    Adapted Agentic Replenishment provider overriding the monolithic control loop
    to bind the Holt-Winters statistical demand forecast.
    """

    def __init__(self, target_coverage_days: int = 14, safety_factor: float = 1.65):
        self.target_coverage_days = target_coverage_days
        self.safety_factor = safety_factor

    @property
    def provider_id(self) -> str:
        return "agentic_statistical_replacement"

    def decide(self, context: OperationalDecisionContext) -> ReplenishmentDecision:
        # Direct perception of inventory state
        on_hand = context.on_hand_inventory
        in_transit = context.in_transit_inventory
        effective_stock = on_hand + in_transit
        daily_d = context.mean_historical_daily_demand
        L = context.supplier_lead_time_days

        # Event awareness factor
        event_factor = 1.2 if (context.event_name and str(context.event_name).strip()) else 1.0

        # Substituted demand model: Statistical Holt-Winters projection
        stat_res = compute_statistical_demand(
            mean_daily=daily_d,
            lead_time_days=L,
            event_name=context.event_name
        )
        lead_time_demand = stat_res["projected_lead_time_demand"]

        # Reorder point calculation with statistical demand
        safety_stock = round(self.safety_factor * daily_d * (L ** 0.5) * event_factor)
        reorder_point = lead_time_demand + safety_stock

        # Direct target stock: ROP + target coverage buffer (7 days)
        target_stock = reorder_point + (daily_d * 7)

        # Autonomous ordering trigger
        if effective_stock <= reorder_point:
            deficit = target_stock - effective_stock
            raw_qty = int(round(deficit))
            # Enforce supplier constraints directly
            order_qty = max(context.minimum_order_quantity, raw_qty)
            order_qty = min(context.maximum_order_quantity, order_qty)

            runway = (effective_stock / daily_d) if daily_d > 0 else 999.0
            timing = "immediate" if runway < L else "soon"
            risk = "high" if runway < L else "medium"
            rationale = (
                f"Agentic Statistical Replacement: Direct ROP trigger (effective {effective_stock} <= ROP {reorder_point:.1f}). "
                f"Ordered {order_qty} units ({timing}). Model={stat_res['model_metadata'].get('model_type')}."
            )
        else:
            order_qty = 0
            timing = "defer"
            risk = "low"
            runway = (effective_stock / daily_d) if daily_d > 0 else 999.0
            rationale = (
                f"Agentic Statistical Replacement: Stock level safe (effective {effective_stock} > ROP {reorder_point:.1f}). "
                f"Runway {runway:.1f}d. Ordering deferred."
            )

        return ReplenishmentDecision(
            order_quantity=order_qty,
            order_timing=timing,
            estimated_demand=round(lead_time_demand, 2),
            rationale=rationale,
            provider_metadata={
                "architecture_pattern": "agentic_statistical_replacement",
                "reorder_point": round(reorder_point, 2),
                "target_stock": round(target_stock, 2),
                "effective_stock": effective_stock,
                "safety_stock": safety_stock,
                "stockout_risk": risk,
                "model_metadata": stat_res["model_metadata"]
            }
        )
