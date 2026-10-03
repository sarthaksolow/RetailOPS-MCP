"""
Common Decision Provider Interface for M5 Operational Simulation.
Establishes the contract for pluggable replenishment decision engines:
- RetailOps MCP-based orchestrator
- Fixed-threshold reorder baseline (s, S policy)
- Literature reproduced architectures
- Human-in-the-loop supervised workflows
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class OperationalDecisionContext:
    """State context presented to a decision provider at simulation day t."""
    series_id: str
    item_id: str
    store_id: str
    category: str
    current_day: int                # Day index 1 to H (1 to 28)
    date: str                       # e.g. "2016-04-25"
    weekday: str
    event_name: Optional[str]
    
    # Inventory state at start of day (before today's demand fulfillment)
    on_hand_inventory: int
    in_transit_inventory: int
    pipeline_orders_count: int
    
    # Historical demand statistics (from training window)
    mean_historical_daily_demand: float
    
    # Supplier parameters
    supplier_lead_time_days: int
    supplier_reliability: float
    minimum_order_quantity: int
    maximum_order_quantity: int
    unit_cost: float
    unit_sell_price: float
    
    # Active scenario metadata
    scenario_id: str


@dataclass
class ReplenishmentDecision:
    """Standardized replenishment decision emitted by any provider."""
    order_quantity: int             # Units to order today (>= 0)
    order_timing: str               # "immediate", "defer", "emergency"
    estimated_demand: float         # Forecasted daily or horizon demand
    rationale: str                  # Explainability string or narrative
    provider_metadata: Dict[str, Any] # Provider-specific debug details


class BaseDecisionProvider(ABC):
    """Abstract base class for all operational replenishment decision providers."""
    
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier (e.g. 'retailops_mcp', 'fixed_threshold_baseline')."""
        pass
    
    @abstractmethod
    def decide(self, context: OperationalDecisionContext) -> ReplenishmentDecision:
        """
        Evaluate operational decision context and return a ReplenishmentDecision.
        Must be deterministic given the context.
        """
        pass


class FixedThresholdDecisionProvider(BaseDecisionProvider):
    """
    Standard (s, S) continuous review inventory policy used as benchmark baseline:
    Reorders when effective inventory (on_hand + in_transit) falls below reorder point s.
    Reorders up to order-up-to level S.
    """
    
    def __init__(self, safety_factor: float = 1.5):
        self.safety_factor = safety_factor

    @property
    def provider_id(self) -> str:
        return "fixed_threshold_baseline"

    def decide(self, context: OperationalDecisionContext) -> ReplenishmentDecision:
        daily_d = context.mean_historical_daily_demand
        L = context.supplier_lead_time_days
        
        # Lead-time demand + safety buffer
        lead_time_demand = daily_d * L
        safety_stock = daily_d * (L ** 0.5) * self.safety_factor
        
        reorder_point = lead_time_demand + safety_stock
        target_stock = reorder_point + (daily_d * 7)  # Target 1-week buffer above s
        
        effective_stock = context.on_hand_inventory + context.in_transit_inventory
        
        if effective_stock <= reorder_point:
            raw_qty = int(round(target_stock - effective_stock))
            # Enforce MOQ
            order_qty = max(context.minimum_order_quantity, raw_qty)
            order_qty = min(context.maximum_order_quantity, order_qty)
            timing = "immediate" if context.on_hand_inventory < (daily_d * 2) else "defer"
            rationale = (f"Fixed threshold triggered: effective stock {effective_stock} <= "
                         f"reorder point {reorder_point:.1f}. Ordering {order_qty} units.")
        else:
            order_qty = 0
            timing = "defer"
            rationale = (f"Sufficient stock: effective stock {effective_stock} > "
                         f"reorder point {reorder_point:.1f}. No reorder.")

        return ReplenishmentDecision(
            order_quantity=order_qty,
            order_timing=timing,
            estimated_demand=round(daily_d, 2),
            rationale=rationale,
            provider_metadata={
                "policy": "s_S_fixed_threshold",
                "reorder_point": round(reorder_point, 2),
                "target_stock": round(target_stock, 2),
                "effective_stock": effective_stock
            }
        )


class RetailOpsDecisionProvider(BaseDecisionProvider):
    """
    Adapter connecting the RetailOps replenishment reasoning pipeline to the M5 operational simulation.
    Preserves exact equations and decision nodes from servers/replenishment/server.py:
    1. Demand volatility weighting (medium -> 1.25x)
    2. Festival / promotional urgency multiplier (1.2x if event within lead time)
    3. Inventory runway calculation (effective_stock / avg_daily_demand)
    4. Lead-time buffered safety stock: round(avg_daily * lead_time * vol_mult * fest_mult)
    5. Order-up-to reorder decision: max(0, int(forecasted_demand + safety_stock - effective_stock))
    6. MOQ and capacity constraint enforcement
    7. Multi-tier timing and risk classification (immediate / soon / defer)
    """

    def __init__(self, default_volatility: str = "medium"):
        self.default_volatility = default_volatility
        self.volatility_map = {"low": 1.1, "medium": 1.25, "high": 1.4}

    @property
    def provider_id(self) -> str:
        return "retailops_mcp"

    def decide(self, context: OperationalDecisionContext) -> ReplenishmentDecision:
        # Translate simulation context into RetailOps input domain
        daily_d = context.mean_historical_daily_demand
        lead_time = context.supplier_lead_time_days
        on_hand = context.on_hand_inventory
        in_transit = context.in_transit_inventory
        effective_stock = on_hand + in_transit

        # Node 1: Demand Risk Node
        volatility_mult = self.volatility_map.get(self.default_volatility, 1.25)

        # Node 2: Festival Urgency Node
        # If event occurs today or is flagged within lead time horizon
        festival_mult = 1.2 if (context.event_name is not None and str(context.event_name).strip() != "") else 1.0

        # Node 3: Inventory Runway Node
        runway_days = (effective_stock / daily_d) if daily_d > 0 else 999.0

        # Node 4: Safety Stock Node
        base_safety = daily_d * lead_time
        safety_stock = round(base_safety * volatility_mult * festival_mult)

        # Node 5: Forecasted Demand over replenishment lead-time window
        forecasted_demand = round(daily_d * lead_time * festival_mult)

        # Node 6: Reorder Decision Node
        target_inventory = forecasted_demand + safety_stock
        raw_qty = max(0, int(target_inventory - effective_stock))

        if raw_qty > 0:
            # Enforce Minimum Order Quantity
            raw_qty = max(raw_qty, context.minimum_order_quantity)
            # Enforce Maximum Order Quantity (capacity constraint)
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
            f"RetailOps Replenishment: order {raw_qty} units ({timing}). "
            f"Stockout risk: {risk}. Stock runway: {runway_days:.1f} days. "
            f"Safety stock: {safety_stock} (vol_mult={volatility_mult}x, fest_mult={festival_mult}x). "
            f"Target: {target_inventory}, Effective: {effective_stock}."
        )

        return ReplenishmentDecision(
            order_quantity=raw_qty,
            order_timing=timing,
            estimated_demand=round(forecasted_demand, 2),
            rationale=rationale,
            provider_metadata={
                "policy": "retailops_reasoning_pipeline",
                "volatility_multiplier": volatility_mult,
                "festival_multiplier": festival_mult,
                "base_safety": round(base_safety, 2),
                "safety_stock": safety_stock,
                "forecasted_demand": forecasted_demand,
                "target_inventory": target_inventory,
                "effective_stock": effective_stock,
                "stock_runway_days": round(runway_days, 1),
                "stockout_risk": risk
            }
        )

