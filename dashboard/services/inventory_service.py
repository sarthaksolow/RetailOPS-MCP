from typing import List, Optional
from dashboard.domain import InventoryItem
from experiments.m5_operational.decision_provider import (
    OperationalDecisionContext,
    RetailOpsDecisionProvider,
)


class InventoryService:
    def __init__(self):
        self._provider = RetailOpsDecisionProvider()
        # Canonical M5 evaluation series definitions
        self._base_items = [
            {
                "series_id": "CA_1_FOODS_1_004",
                "item_id": "FOODS_1_004",
                "store_id": "CA_1",
                "category": "FOODS",
                "unit_cost": 1.18,
                "unit_sell_price": 1.96,
                "on_hand": 14,
                "in_transit": 20,
                "daily_demand": 3.5,
                "lead_time": 7,
            },
            {
                "series_id": "CA_1_FOODS_1_012",
                "item_id": "FOODS_1_012",
                "store_id": "CA_1",
                "category": "FOODS",
                "unit_cost": 3.38,
                "unit_sell_price": 5.64,
                "on_hand": 8,
                "in_transit": 0,
                "daily_demand": 2.2,
                "lead_time": 7,
            },
            {
                "series_id": "CA_1_HOUSEHOLD_1_007",
                "item_id": "HOUSEHOLD_1_007",
                "store_id": "CA_1",
                "category": "HOUSEHOLD",
                "unit_cost": 0.89,
                "unit_sell_price": 1.48,
                "on_hand": 26,
                "in_transit": 15,
                "daily_demand": 4.1,
                "lead_time": 7,
            },
            {
                "series_id": "CA_1_HOBBIES_1_004",
                "item_id": "HOBBIES_1_004",
                "store_id": "CA_1",
                "category": "HOBBIES",
                "unit_cost": 2.78,
                "unit_sell_price": 4.64,
                "on_hand": 4,
                "in_transit": 0,
                "daily_demand": 1.75,
                "lead_time": 7,
            },
            {
                "series_id": "CA_1_HOBBIES_1_008",
                "item_id": "HOBBIES_1_008",
                "store_id": "CA_1",
                "category": "HOBBIES",
                "unit_cost": 0.29,
                "unit_sell_price": 0.48,
                "on_hand": 65,
                "in_transit": 40,
                "daily_demand": 11.2,
                "lead_time": 7,
            },
        ]

    def get_inventory_items(self) -> List[InventoryItem]:
        items: List[InventoryItem] = []
        for raw in self._base_items:
            runway = round(raw["on_hand"] / max(raw["daily_demand"], 0.1), 1)
            risk = "low"
            if runway < raw["lead_time"]:
                risk = "high"
            elif runway < (raw["lead_time"] * 1.5):
                risk = "medium"

            # Query RetailOps decision provider for recommendation
            ctx = OperationalDecisionContext(
                series_id=raw["series_id"],
                item_id=raw["item_id"],
                store_id=raw["store_id"],
                category=raw["category"],
                current_day=5,
                date="2016-04-29",
                weekday="Friday",
                event_name=None,
                on_hand_inventory=raw["on_hand"],
                in_transit_inventory=raw["in_transit"],
                pipeline_orders_count=1 if raw["in_transit"] > 0 else 0,
                mean_historical_daily_demand=raw["daily_demand"],
                supplier_lead_time_days=raw["lead_time"],
                supplier_reliability=0.95,
                minimum_order_quantity=20,
                maximum_order_quantity=500,
                unit_cost=raw["unit_cost"],
                unit_sell_price=raw["unit_sell_price"],
                scenario_id="SCEN-01",
            )
            decision = self._provider.decide(ctx)

            items.append(
                InventoryItem(
                    series_id=raw["series_id"],
                    item_id=raw["item_id"],
                    store_id=raw["store_id"],
                    category=raw["category"],
                    unit_cost=raw["unit_cost"],
                    unit_sell_price=raw["unit_sell_price"],
                    on_hand=raw["on_hand"],
                    in_transit=raw["in_transit"],
                    daily_demand=raw["daily_demand"],
                    lead_time_days=raw["lead_time"],
                    runway_days=runway,
                    stockout_risk=risk,
                    recommended_order=decision.order_quantity,
                )
            )
        return items

    def get_item_by_id(self, series_id: str) -> Optional[InventoryItem]:
        for item in self.get_inventory_items():
            if item.series_id == series_id:
                return item
        return None
