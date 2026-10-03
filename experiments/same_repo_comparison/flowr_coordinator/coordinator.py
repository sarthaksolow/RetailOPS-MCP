"""
Flowr Coordinator Architecture Pattern.
Reference: Bandara et al. (2026), arXiv:2604.05987.
Implements the bounded Centralized Reasoning Coordinator pattern:
Operational Context -> Central Coordinator -> Modular Domain Functions -> Synthesized Decision.
"""
from typing import Dict, Any, List, Optional
from experiments.m5_operational.decision_provider import (
    BaseDecisionProvider,
    OperationalDecisionContext,
    ReplenishmentDecision
)


class FlowrDomainTools:
    """Modular domain functions mediated by the central coordinator."""

    @staticmethod
    def monitor_inventory(context: OperationalDecisionContext) -> Dict[str, Any]:
        """Domain tool: Assesses stock runway, in-transit orders, and immediate stockout risk."""
        on_hand = context.on_hand_inventory
        in_transit = context.in_transit_inventory
        effective_stock = on_hand + in_transit
        daily_d = context.mean_historical_daily_demand
        runway = (effective_stock / daily_d) if daily_d > 0 else 999.0

        risk_level = "low"
        if runway < context.supplier_lead_time_days:
            risk_level = "high"
        elif runway < (context.supplier_lead_time_days + 7):
            risk_level = "medium"

        return {
            "on_hand": on_hand,
            "in_transit": in_transit,
            "effective_stock": effective_stock,
            "runway_days": round(runway, 1),
            "stockout_risk": risk_level
        }

    @staticmethod
    def forecast_demand(context: OperationalDecisionContext) -> Dict[str, Any]:
        """Domain tool: Generates lead-time demand projection incorporating event signals."""
        daily_d = context.mean_historical_daily_demand
        L = context.supplier_lead_time_days
        event_surge = 1.2 if (context.event_name and str(context.event_name).strip()) else 1.0
        lead_time_demand = round(daily_d * L * event_surge, 2)
        return {
            "mean_daily": daily_d,
            "horizon_days": L,
            "event_surge_factor": event_surge,
            "projected_lead_time_demand": lead_time_demand
        }

    @staticmethod
    def plan_procurement(
        context: OperationalDecisionContext,
        inv_state: Dict[str, Any],
        demand_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Domain tool: Calculates order requirement using coordinator balancing buffer."""
        daily_d = context.mean_historical_daily_demand
        L = context.supplier_lead_time_days
        effective_stock = inv_state["effective_stock"]
        projected_demand = demand_info["projected_lead_time_demand"]

        # Coordinator safety buffer: 1.8 * d * sqrt(L)
        safety_buffer = round(1.8 * daily_d * (L ** 0.5))
        target_stock = projected_demand + safety_buffer

        raw_needed = max(0, int(round(target_stock - effective_stock)))
        return {
            "target_stock": target_stock,
            "safety_buffer": safety_buffer,
            "raw_needed_units": raw_needed
        }

    @staticmethod
    def coordinate_supplier(
        context: OperationalDecisionContext,
        procurement: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Domain tool: Enforces supplier constraints (MOQ, maximum capacity)."""
        raw_qty = procurement["raw_needed_units"]
        moq = context.minimum_order_quantity
        max_oq = context.maximum_order_quantity

        final_qty = 0
        if raw_qty > 0:
            final_qty = max(moq, raw_qty)
            final_qty = min(max_oq, final_qty)

        return {
            "recommended_order_quantity": final_qty,
            "moq_applied": (raw_qty > 0 and raw_qty < moq),
            "capacity_capped": (raw_qty > max_oq)
        }


class FlowrCoordinatorDecisionProvider(BaseDecisionProvider):
    """
    Centralized Reasoning Coordinator architecture pattern (Flowr).
    Evaluates state, coordinates modular domain tools, and synthesizes replenishment decision.
    """

    def __init__(self):
        self.tools = FlowrDomainTools()

    @property
    def provider_id(self) -> str:
        return "flowr_coordinator"

    def decide(self, context: OperationalDecisionContext) -> ReplenishmentDecision:
        tool_invocation_trace: List[str] = []

        # Step 1: Central coordinator queries Inventory Monitoring tool
        inv_state = self.tools.monitor_inventory(context)
        tool_invocation_trace.append("monitor_inventory")

        # Step 2: Coordinator determines if replenishment action is needed
        runway = inv_state["runway_days"]
        L = context.supplier_lead_time_days
        stockout_risk = inv_state["stockout_risk"]

        if stockout_risk in ("high", "medium"):
            # Step 3: Coordinator queries Demand Forecasting tool
            demand_info = self.tools.forecast_demand(context)
            tool_invocation_trace.append("forecast_demand")

            # Step 4: Coordinator queries Procurement Planning tool
            procurement = self.tools.plan_procurement(context, inv_state, demand_info)
            tool_invocation_trace.append("plan_procurement")

            # Step 5: Coordinator queries Supplier Coordination tool
            supplier_eval = self.tools.coordinate_supplier(context, procurement)
            tool_invocation_trace.append("coordinate_supplier")

            final_qty = supplier_eval["recommended_order_quantity"]
            timing = "immediate" if stockout_risk == "high" else "soon"
            rationale = (
                f"Flowr Coordinator: Action triggered by {stockout_risk} risk (runway={runway}d). "
                f"Dispatched {len(tool_invocation_trace)} domain tools. "
                f"Target={procurement['target_stock']}, Order={final_qty}."
            )
            estimated_d = demand_info["projected_lead_time_demand"]
            target_stock = procurement["target_stock"]
            safety_buffer = procurement["safety_buffer"]
        else:
            # Low risk: Coordinator defers procurement without invoking downstream supplier tools
            final_qty = 0
            timing = "defer"
            rationale = (
                f"Flowr Coordinator: Stock runway ({runway}d >= L={L}d + 7) sufficient. "
                f"Downstream procurement queries deferred by coordinator."
            )
            estimated_d = round(context.mean_historical_daily_demand * L, 2)
            target_stock = inv_state["effective_stock"]
            safety_buffer = 0

        return ReplenishmentDecision(
            order_quantity=final_qty,
            order_timing=timing,
            estimated_demand=estimated_d,
            rationale=rationale,
            provider_metadata={
                "architecture_pattern": "flowr_centralized_coordinator",
                "tool_invocations": tool_invocation_trace,
                "inventory_runway_days": runway,
                "stockout_risk": stockout_risk,
                "target_stock": target_stock,
                "safety_buffer": safety_buffer,
                "effective_stock": inv_state["effective_stock"]
            }
        )
