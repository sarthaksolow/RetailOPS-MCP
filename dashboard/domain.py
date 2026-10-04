from dataclasses import dataclass
from typing import List, Optional


@dataclass
class InventoryItem:
    series_id: str
    item_id: str
    store_id: str
    category: str
    unit_cost: float
    unit_sell_price: float
    on_hand: int
    in_transit: int
    daily_demand: float
    lead_time_days: int
    runway_days: float
    stockout_risk: str
    recommended_order: int


@dataclass
class Decision:
    id: str
    series_id: str
    item_id: str
    category: str
    proposed_qty: int
    final_qty: int
    urgency: str
    stockout_risk: str
    requires_approval: bool
    status: str
    reason: str
    operator_action: str
    notes: str
    order_cost: float


@dataclass
class ServiceStatus:
    name: str
    role: str
    transport: str
    status: str
    tool_count: int
    tools: List[str]
    latency_ms: float


@dataclass
class MetricCardData:
    title: str
    value: str
    subtitle: str
    trend: Optional[str] = None
