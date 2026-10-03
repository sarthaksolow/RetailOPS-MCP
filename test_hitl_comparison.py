"""
Unit and Regression Test Suite for Step 11: Human-in-the-Loop (HITL) Comparison.
Verifies:
1. Both Autonomous and Supervised providers inherit from BaseDecisionProvider.
2. Identical OperationalDecisionContext is accepted and returns valid ReplenishmentDecision.
3. Decision context immutability (input context is not altered).
4. Operator governance policy rules (budget capping, horizon boundary, emergency validation).
5. Latency accounting (autonomous zero latency vs supervised escalation latency).
6. Deterministic reproducibility across repeated evaluations.
7. Inventory conservation and zero constraint violations in full simulation runs.
"""
import unittest
import copy
import sys
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent
if REPO_ROOT.name == "hitl_comparison":
    REPO_ROOT = REPO_ROOT.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.m5_operational.decision_provider import (
    BaseDecisionProvider,
    OperationalDecisionContext,
    ReplenishmentDecision,
)
from experiments.hitl_comparison.hitl_provider import (
    RetailOpsAutonomousProvider,
    RetailOpsSupervisedProvider,
)
from experiments.m5_operational.scenarios import get_scenario
from experiments.m5_operational.simulator import InventorySimulator


class TestHITLComparison(unittest.TestCase):

    def setUp(self):
        self.autonomous_provider = RetailOpsAutonomousProvider()
        self.supervised_provider = RetailOpsSupervisedProvider()

        self.sample_context = OperationalDecisionContext(
            series_id="CA_1_FOODS_1_004",
            item_id="FOODS_1_004",
            store_id="CA_1",
            category="FOODS",
            current_day=5,
            date="2016-04-29",
            weekday="Friday",
            event_name=None,
            on_hand_inventory=14,
            in_transit_inventory=20,
            pipeline_orders_count=1,
            mean_historical_daily_demand=3.5,
            supplier_lead_time_days=7,
            supplier_reliability=0.95,
            minimum_order_quantity=20,
            maximum_order_quantity=500,
            unit_cost=1.18,
            unit_sell_price=1.96,
            scenario_id="SCEN-01"
        )

        self.mock_series = {
            "metadata": {
                "series_id": "CA_1_FOODS_1_004",
                "item_id": "FOODS_1_004",
                "store_id": "CA_1",
                "cat_id": "FOODS",
                "dept_id": "FOODS_1",
                "unit_sell_price": 1.96,
                "unit_procurement_cost": 1.18,
                "holding_cost_rate": 0.001
            },
            "train_records": [{"sales": 3} for _ in range(100)],
            "eval_records": [
                {
                    "d": f"d_{1913+i}",
                    "day_index": 1913 + i,
                    "date": f"2016-05-{i:02d}",
                    "weekday": "Monday",
                    "event_name": None,
                    "sales": 4
                }
                for i in range(1, 29)
            ]
        }

    def test_provider_inheritance(self):
        """Verifies both providers inherit from BaseDecisionProvider."""
        self.assertIsInstance(self.autonomous_provider, BaseDecisionProvider)
        self.assertIsInstance(self.supervised_provider, BaseDecisionProvider)
        self.assertEqual(self.autonomous_provider.provider_id, "retailops_autonomous")
        self.assertEqual(self.supervised_provider.provider_id, "retailops_human_supervised")

    def test_schema_compliance(self):
        """Verifies both providers return valid ReplenishmentDecision schemas."""
        dec_auto = self.autonomous_provider.decide(self.sample_context)
        dec_sup = self.supervised_provider.decide(self.sample_context)

        for dec in [dec_auto, dec_sup]:
            self.assertIsInstance(dec, ReplenishmentDecision)
            self.assertIsInstance(dec.order_quantity, int)
            self.assertGreaterEqual(dec.order_quantity, 0)
            self.assertIn(dec.order_timing, ["immediate", "soon", "defer"])
            self.assertIsInstance(dec.rationale, str)
            self.assertIsInstance(dec.provider_metadata, dict)

    def test_context_immutability(self):
        """Verifies neither provider mutates the incoming decision context."""
        ctx_copy = copy.deepcopy(self.sample_context)
        _ = self.autonomous_provider.decide(self.sample_context)
        self.assertEqual(self.sample_context.__dict__, ctx_copy.__dict__)

        _ = self.supervised_provider.decide(self.sample_context)
        self.assertEqual(self.sample_context.__dict__, ctx_copy.__dict__)

    def test_autonomous_mode_metadata(self):
        """Verifies autonomous provider records 0 escalations and 0 simulated latency."""
        dec = self.autonomous_provider.decide(self.sample_context)
        meta = dec.provider_metadata
        self.assertEqual(meta["hitl_mode"], "autonomous")
        self.assertFalse(meta["gate_triggered"])
        self.assertFalse(meta["escalated"])
        self.assertEqual(meta["operator_action"], "NONE")
        self.assertEqual(meta["approval_latency_seconds"], 0.0)
        self.assertFalse(meta["policy_violation_prevented"])

    def test_supervised_horizon_boundary_override(self):
        """
        Verifies human supervisor overrides orders when current_day + lead_time > 28
        and on-hand stock runway is sufficient for remainder of horizon.
        """
        late_context = OperationalDecisionContext(
            series_id="CA_1_HOBBIES_1_004",
            item_id="HOBBIES_1_004",
            store_id="CA_1",
            category="HOBBIES",
            current_day=23,
            date="2016-05-17",
            weekday="Tuesday",
            event_name=None,
            on_hand_inventory=15,  # sufficient for 5 remaining days at ~1.75 demand
            in_transit_inventory=0,
            pipeline_orders_count=0,
            mean_historical_daily_demand=1.75,
            supplier_lead_time_days=7,  # 23 + 7 = 30 > 28
            supplier_reliability=0.95,
            minimum_order_quantity=20,
            maximum_order_quantity=500,
            unit_cost=2.78,
            unit_sell_price=4.63,
            scenario_id="SCEN-01"
        )
        dec = self.supervised_provider.decide(late_context)
        # Should be overridden to 0 because arrival (day 30) is outside 28-day horizon
        self.assertEqual(dec.order_quantity, 0)
        meta = dec.provider_metadata
        self.assertEqual(meta["operator_action"], "OVERRIDE")
        self.assertTrue(meta["policy_violation_prevented"])
        self.assertEqual(meta["approval_latency_seconds"], 15.0)

    def test_supervised_budget_capping_override(self):
        """
        Verifies human supervisor caps orders exceeding the single-order budget limit ($100).
        """
        high_cost_context = OperationalDecisionContext(
            series_id="CA_1_HOBBIES_1_008",
            item_id="HOBBIES_1_008",
            store_id="CA_1",
            category="HOBBIES",
            current_day=5,
            date="2016-04-29",
            weekday="Friday",
            event_name=None,
            on_hand_inventory=30,  # runway ~ 2.5d
            in_transit_inventory=0,
            pipeline_orders_count=0,
            mean_historical_daily_demand=12.0,
            supplier_lead_time_days=7,
            supplier_reliability=0.95,
            minimum_order_quantity=20,
            maximum_order_quantity=500,
            unit_cost=2.0,  # $2/unit, proposed 159 units = $318 > $100 cap
            unit_sell_price=15.0,
            scenario_id="SCEN-01"
        )
        dec = self.supervised_provider.decide(high_cost_context)
        total_order_cost = dec.order_quantity * high_cost_context.unit_cost
        meta = dec.provider_metadata
        self.assertEqual(meta["operator_action"], "OVERRIDE")
        self.assertTrue(meta["policy_violation_prevented"])
        self.assertLessEqual(total_order_cost, 100.0)
        self.assertEqual(dec.order_quantity, 50)

    def test_supervised_emergency_approval(self):
        """
        Verifies supervisor approves emergency order when inventory runway is critical (<= 2 days).
        """
        emergency_context = OperationalDecisionContext(
            series_id="CA_1_FOODS_1_004",
            item_id="FOODS_1_004",
            store_id="CA_1",
            category="FOODS",
            current_day=5,
            date="2016-04-29",
            weekday="Friday",
            event_name=None,
            on_hand_inventory=2,  # runway ~ 0.57 days (< 2.0d)
            in_transit_inventory=0,
            pipeline_orders_count=0,
            mean_historical_daily_demand=3.5,
            supplier_lead_time_days=7,
            supplier_reliability=0.95,
            minimum_order_quantity=20,
            maximum_order_quantity=500,
            unit_cost=1.18,  # 20 * 1.18 = $23.60 < $100 budget
            unit_sell_price=1.96,
            scenario_id="SCEN-01"
        )
        dec = self.supervised_provider.decide(emergency_context)
        meta = dec.provider_metadata
        self.assertGreater(dec.order_quantity, 0)
        self.assertEqual(meta["operator_action"], "APPROVE")
        self.assertFalse(meta["policy_violation_prevented"])

    def test_bit_for_bit_determinism(self):
        """Verifies repeated decisions produce identical results."""
        p1 = RetailOpsSupervisedProvider()
        p2 = RetailOpsSupervisedProvider()
        dec1 = p1.decide(self.sample_context)
        dec2 = p2.decide(self.sample_context)

        self.assertEqual(dec1.order_quantity, dec2.order_quantity)
        self.assertEqual(dec1.order_timing, dec2.order_timing)
        self.assertEqual(dec1.provider_metadata, dec2.provider_metadata)

    def test_end_to_end_simulation(self):
        """
        Runs an end-to-end simulation for both autonomous and supervised modes.
        Verifies inventory conservation and zero constraint violations.
        """
        scenario = get_scenario("SCEN-01")
        sim = InventorySimulator(scenario)

        for provider in [self.autonomous_provider, self.supervised_provider]:
            res = sim.run_simulation(self.mock_series, provider)
            self.assertEqual(res.constraint_violations_count, 0, f"Constraint violations for {provider.provider_id}")
            self.assertEqual(len(res.daily_trace), 28)

            init_inv = res.daily_trace[0].starting_inventory
            recv = sum(l.arrivals for l in res.daily_trace)
            ful = res.total_fulfilled
            end_inv = res.daily_trace[-1].ending_inventory
            self.assertEqual(end_inv, init_inv + recv - ful, f"Conservation broken for {provider.provider_id}")


if __name__ == "__main__":
    unittest.main()
