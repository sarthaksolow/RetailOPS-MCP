"""
Agentic Inventory Replenishment Architecture Pattern.
Reference: Syed et al. (ICBDT 2025), arXiv:2511.23366.
Implements the bounded Direct Single-Domain Autonomous Replenishment pattern:
Inventory State + Demand Signals + Supplier Constraints -> Direct Replenishment Decision.
"""
from typing import Dict, Any
from experiments.m5_operational.decision_provider import (
    BaseDecisionProvider,
    OperationalDecisionContext,
    ReplenishmentDecision
)


class AgenticReplenishmentDecisionProvider(BaseDecisionProvider):
    """
    Direct Single-Domain Autonomous Agent architecture pattern.
    Unbundled single-node control loop directly coupling perception of inventory
    and supplier constraints into an immediate purchase order decision.
    """

    def __init__(self, target_coverage_days: int = 14, safety_factor: float = 1.65):
        self.target_coverage_days = target_coverage_days
        self.safety_factor = safety_factor

    @property
    def provider_id(self) -> str:
        return "agentic_replenishment"

    def decide(self, context: OperationalDecisionContext) -> ReplenishmentDecision:
        # Direct perception of inventory state
        on_hand = context.on_hand_inventory
        in_transit = context.in_transit_inventory
        effective_stock = on_hand + in_transit
        daily_d = context.mean_historical_daily_demand
        L = context.supplier_lead_time_days

        # Event awareness directly incorporated
        event_factor = 1.2 if (context.event_name and str(context.event_name).strip()) else 1.0

        # Direct reorder point (ROP) calculation: Lead time demand + safety stock
        lead_time_demand = daily_d * L * event_factor
        safety_stock = round(self.safety_factor * daily_d * (L ** 0.5) * event_factor)
        reorder_point = lead_time_demand + safety_stock

        # Direct target stock: ROP + target coverage buffer (e.g. 7-14 days)
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
                f"Agentic Replenishment: Direct ROP trigger (effective {effective_stock} <= ROP {reorder_point:.1f}). "
                f"Ordered {order_qty} units ({timing}). Safety stock={safety_stock}."
            )
        else:
            order_qty = 0
            timing = "defer"
            risk = "low"
            runway = (effective_stock / daily_d) if daily_d > 0 else 999.0
            rationale = (
                f"Agentic Replenishment: Stock level safe (effective {effective_stock} > ROP {reorder_point:.1f}). "
                f"Runway {runway:.1f}d. Ordering deferred."
            )

        return ReplenishmentDecision(
            order_quantity=order_qty,
            order_timing=timing,
            estimated_demand=round(lead_time_demand, 2),
            rationale=rationale,
            provider_metadata={
                "architecture_pattern": "agentic_direct_replenishment",
                "reorder_point": round(reorder_point, 2),
                "target_stock": round(target_stock, 2),
                "effective_stock": effective_stock,
                "safety_stock": safety_stock,
                "stockout_risk": risk
            }
        )
