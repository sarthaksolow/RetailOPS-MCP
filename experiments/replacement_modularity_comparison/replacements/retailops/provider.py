"""
RetailOps MCP Statistical Replacement Provider.
Demonstrates contract-preserving modularity under Model Context Protocol.
The forecasting service is replaced via configuration change; the surrounding
replenishment reasoning pipeline and orchestrator logic remain 100% unchanged.
"""
from typing import Dict, Any
from experiments.m5_operational.decision_provider import (
    BaseDecisionProvider,
    OperationalDecisionContext,
    ReplenishmentDecision
)
from experiments.replacement_modularity_comparison.statistical_model import compute_statistical_demand


class RetailOpsStatisticalReplacementProvider(BaseDecisionProvider):
    """
    RetailOps decision provider consuming the statistical forecasting service.
    Preserves exact decision equations from servers/replenishment/server.py
    while binding the Holt-Winters statistical demand forecast.
    """

    def __init__(self, default_volatility: str = "medium"):
        self.default_volatility = default_volatility
        self.volatility_map = {"low": 1.1, "medium": 1.25, "high": 1.4}

    @property
    def provider_id(self) -> str:
        return "retailops_statistical_replacement"

    def decide(self, context: OperationalDecisionContext) -> ReplenishmentDecision:
        daily_d = context.mean_historical_daily_demand
        lead_time = context.supplier_lead_time_days
        on_hand = context.on_hand_inventory
        in_transit = context.in_transit_inventory
        effective_stock = on_hand + in_transit

        # Node 1: Demand Risk Node
        volatility_mult = self.volatility_map.get(self.default_volatility, 1.25)

        # Node 2: Festival Urgency Node
        festival_mult = 1.2 if (context.event_name is not None and str(context.event_name).strip() != "") else 1.0

        # Node 3: Inventory Runway Node
        runway_days = (effective_stock / daily_d) if daily_d > 0 else 999.0

        # Node 4: Safety Stock Node
        base_safety = daily_d * lead_time
        safety_stock = round(base_safety * volatility_mult * festival_mult)

        # Node 5: Forecasted Demand from Replacement Statistical Service
        stat_forecast = compute_statistical_demand(
            mean_daily=daily_d,
            lead_time_days=lead_time,
            event_name=context.event_name
        )
        forecasted_demand = round(stat_forecast["projected_lead_time_demand"])

        # Node 6: Reorder Decision Node
        target_inventory = forecasted_demand + safety_stock
        raw_qty = max(0, int(target_inventory - effective_stock))

        if raw_qty > 0:
            raw_qty = max(raw_qty, context.minimum_order_quantity)
            raw_qty = min(raw_qty, context.maximum_order_quantity)

        # Node 7: Timing and Risk Node
        if runway_days < lead_time:
            timing = "immediate"
            risk = "high"
        elif runway_days < 30:
            timing = "soon"
            risk = "medium"
        else:
            timing = "defer"
            risk = "low"

        rationale = (
            f"RetailOps Statistical Replacement: order {raw_qty} units ({timing}). "
            f"Model: {stat_forecast['model_metadata'].get('model_type', 'holt_winters')}. "
            f"Stockout risk: {risk}. Stock runway: {runway_days:.1f} days. "
            f"Safety stock: {safety_stock}. Target: {target_inventory}, Effective: {effective_stock}."
        )

        return ReplenishmentDecision(
            order_quantity=raw_qty,
            order_timing=timing,
            estimated_demand=round(forecasted_demand, 2),
            rationale=rationale,
            provider_metadata={
                "policy": "retailops_statistical_replacement_pipeline",
                "service_contract": "getForecast_compatible",
                "volatility_multiplier": volatility_mult,
                "festival_multiplier": festival_mult,
                "safety_stock": safety_stock,
                "forecasted_demand": forecasted_demand,
                "target_inventory": target_inventory,
                "effective_stock": effective_stock,
                "stock_runway_days": round(runway_days, 1),
                "stockout_risk": risk,
                "model_metadata": stat_forecast["model_metadata"]
            }
        )
