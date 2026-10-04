from typing import List, Optional, Dict, Any
from dashboard.domain import Decision
from experiments.m5_operational.decision_provider import (
    OperationalDecisionContext,
    RetailOpsDecisionProvider,
)
from experiments.hitl_comparison.hitl_provider import RetailOpsSupervisedProvider


class DecisionService:
    def __init__(self):
        self._provider = RetailOpsDecisionProvider()
        self._supervised = RetailOpsSupervisedProvider()
        self._decisions: Dict[str, Decision] = {}
        self._init_default_decisions()

    def _init_default_decisions(self):
        # Generate initial operational decisions for active items
        test_cases = [
            {
                "id": "DEC-101",
                "series_id": "CA_1_HOBBIES_1_004",
                "item_id": "HOBBIES_1_004",
                "category": "HOBBIES",
                "on_hand": 4,
                "in_transit": 0,
                "daily_demand": 1.75,
                "lead_time": 7,
                "unit_cost": 2.78,
                "unit_sell_price": 4.64,
                "current_day": 5,
            },
            {
                "id": "DEC-102",
                "series_id": "CA_1_HOBBIES_1_008",
                "item_id": "HOBBIES_1_008",
                "category": "HOBBIES",
                "on_hand": 10,
                "in_transit": 0,
                "daily_demand": 11.2,
                "lead_time": 7,
                "unit_cost": 0.29,
                "unit_sell_price": 0.48,
                "current_day": 5,
            },
            {
                "id": "DEC-103",
                "series_id": "CA_1_FOODS_1_004",
                "item_id": "FOODS_1_004",
                "category": "FOODS",
                "on_hand": 2,
                "in_transit": 0,
                "daily_demand": 3.5,
                "lead_time": 7,
                "unit_cost": 1.18,
                "unit_sell_price": 1.96,
                "current_day": 5,
            },
            {
                "id": "DEC-104",
                "series_id": "CA_1_FOODS_1_012",
                "item_id": "FOODS_1_012",
                "category": "FOODS",
                "on_hand": 8,
                "in_transit": 0,
                "daily_demand": 2.2,
                "lead_time": 7,
                "unit_cost": 3.38,
                "unit_sell_price": 5.64,
                "current_day": 5,
            },
            {
                "id": "DEC-105",
                "series_id": "CA_1_HOUSEHOLD_1_007",
                "item_id": "HOUSEHOLD_1_007",
                "category": "HOUSEHOLD",
                "on_hand": 26,
                "in_transit": 15,
                "daily_demand": 4.1,
                "lead_time": 7,
                "unit_cost": 0.89,
                "unit_sell_price": 1.48,
                "current_day": 5,
            },
            {
                "id": "DEC-106",
                "series_id": "CA_1_HOBBIES_1_004",
                "item_id": "HOBBIES_1_004",
                "category": "HOBBIES",
                "on_hand": 15,
                "in_transit": 0,
                "daily_demand": 1.75,
                "lead_time": 7,
                "unit_cost": 2.78,
                "unit_sell_price": 4.64,
                "current_day": 23,  # Horizon boundary trigger: 23 + 7 = 30 > 28
            },
        ]

        for tc in test_cases:
            ctx = OperationalDecisionContext(
                series_id=tc["series_id"],
                item_id=tc["item_id"],
                store_id="CA_1",
                category=tc["category"],
                current_day=tc["current_day"],
                date="2016-04-29",
                weekday="Friday",
                event_name=None,
                on_hand_inventory=tc["on_hand"],
                in_transit_inventory=tc["in_transit"],
                pipeline_orders_count=1 if tc["in_transit"] > 0 else 0,
                mean_historical_daily_demand=tc["daily_demand"],
                supplier_lead_time_days=tc["lead_time"],
                supplier_reliability=0.95,
                minimum_order_quantity=20,
                maximum_order_quantity=500,
                unit_cost=tc["unit_cost"],
                unit_sell_price=tc["unit_sell_price"],
                scenario_id="SCEN-01",
            )
            # Evaluate via supervised provider to check approval gate triggers
            sup_dec = self._supervised.decide(ctx)
            meta = sup_dec.provider_metadata
            req_approval = meta.get("escalated", False)
            risk = meta.get("stockout_risk", "low")
            order_cost = round(sup_dec.order_quantity * tc["unit_cost"], 2)

            self._decisions[tc["id"]] = Decision(
                id=tc["id"],
                series_id=tc["series_id"],
                item_id=tc["item_id"],
                category=tc["category"],
                proposed_qty=meta.get("original_proposed_quantity", sup_dec.order_quantity),
                final_qty=sup_dec.order_quantity,
                urgency=sup_dec.order_timing,
                stockout_risk=risk,
                requires_approval=req_approval,
                status="Pending Review" if req_approval else "Auto-Approved",
                reason=sup_dec.rationale,
                operator_action="PENDING" if req_approval else "APPROVE",
                notes=meta.get("operator_notes", ""),
                order_cost=order_cost,
            )

    def get_all_decisions(self) -> List[Decision]:
        return list(self._decisions.values())

    def get_decision(self, decision_id: str) -> Optional[Decision]:
        return self._decisions.get(decision_id)

    def approve_decision(self, decision_id: str) -> Optional[Decision]:
        dec = self._decisions.get(decision_id)
        if dec:
            dec.status = "Approved"
            dec.operator_action = "APPROVE"
            dec.notes = "Supervisory approval granted by retail operations manager."
        return dec

    def override_decision(self, decision_id: str, new_quantity: int, notes: str) -> Optional[Decision]:
        dec = self._decisions.get(decision_id)
        if dec:
            dec.final_qty = max(0, new_quantity)
            dec.status = "Overridden"
            dec.operator_action = "OVERRIDE"
            dec.notes = notes or f"Manual override to {new_quantity} units."
        return dec
