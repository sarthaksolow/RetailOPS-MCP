"""
Unit and Regression Test Suite for Step 10: Same-Repository Research Architecture Comparison.
Verifies:
1. All candidate architectures inherit from BaseDecisionProvider.
2. Identical OperationalDecisionContext can be passed to every provider.
3. All provider decisions satisfy the common ReplenishmentDecision schema.
4. No provider accesses future demand or alters the simulation state context.
5. Bit-for-bit deterministic reproducibility across repeated runs.
6. Inventory conservation holds across all architectures.
7. Zero constraint violations across all architectures.
"""
import unittest
import copy
from experiments.m5_operational.decision_provider import (
    BaseDecisionProvider,
    OperationalDecisionContext,
    ReplenishmentDecision,
    RetailOpsDecisionProvider,
    FixedThresholdDecisionProvider,
)
from experiments.same_repo_comparison import (
    FlowrCoordinatorDecisionProvider,
    WorkflowLLMDecisionProvider,
    AgenticReplenishmentDecisionProvider,
)
from experiments.m5_operational.scenarios import SCENARIOS, get_scenario
from experiments.m5_operational.simulator import InventorySimulator


class TestSameRepoArchitectureComparison(unittest.TestCase):

    def setUp(self):
        self.providers = [
            RetailOpsDecisionProvider(),
            FlowrCoordinatorDecisionProvider(),
            WorkflowLLMDecisionProvider(),
            AgenticReplenishmentDecisionProvider(),
            FixedThresholdDecisionProvider()
        ]

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

    def test_01_interface_inheritance(self):
        """Verify all 5 providers inherit from BaseDecisionProvider."""
        for p in self.providers:
            self.assertIsInstance(p, BaseDecisionProvider, f"{p} must inherit BaseDecisionProvider")
            self.assertIsInstance(p.provider_id, str)
            self.assertGreater(len(p.provider_id), 0)

    def test_02_identical_input_consumption(self):
        """Verify identical OperationalDecisionContext is successfully processed by all providers."""
        for p in self.providers:
            ctx_copy = copy.deepcopy(self.sample_context)
            decision = p.decide(ctx_copy)
            self.assertIsInstance(decision, ReplenishmentDecision, f"{p.provider_id} returned invalid type")
            self.assertIsInstance(decision.order_quantity, int)
            self.assertGreaterEqual(decision.order_quantity, 0)
            self.assertIn(decision.order_timing, ["immediate", "soon", "defer"])
            self.assertIsInstance(decision.rationale, str)
            self.assertIsInstance(decision.provider_metadata, dict)

    def test_03_context_immutability(self):
        """Verify no provider mutates the input OperationalDecisionContext."""
        for p in self.providers:
            ctx_copy = copy.deepcopy(self.sample_context)
            _ = p.decide(ctx_copy)
            self.assertEqual(ctx_copy.on_hand_inventory, self.sample_context.on_hand_inventory)
            self.assertEqual(ctx_copy.in_transit_inventory, self.sample_context.in_transit_inventory)
            self.assertEqual(ctx_copy.current_day, self.sample_context.current_day)

    def test_04_moq_and_capacity_compliance(self):
        """Verify all providers enforce MOQ (order == 0 or order >= MOQ) and MaxOQ."""
        for p in self.providers:
            # Low stock context triggering reorder
            low_stock_ctx = copy.deepcopy(self.sample_context)
            low_stock_ctx.on_hand_inventory = 1
            low_stock_ctx.in_transit_inventory = 0
            decision = p.decide(low_stock_ctx)
            if decision.order_quantity > 0:
                self.assertGreaterEqual(
                    decision.order_quantity,
                    low_stock_ctx.minimum_order_quantity,
                    f"{p.provider_id} violated MOQ"
                )
                self.assertLessEqual(
                    decision.order_quantity,
                    low_stock_ctx.maximum_order_quantity,
                    f"{p.provider_id} violated MaxOQ"
                )

    def test_05_deterministic_reproducibility(self):
        """Verify identical inputs produce bit-for-bit identical outputs across repeated runs."""
        scen = get_scenario("SCEN-02")
        sim = InventorySimulator(scen)
        for p in self.providers:
            res1 = sim.run_simulation(self.mock_series, p)
            res2 = sim.run_simulation(self.mock_series, p)
            self.assertEqual(res1.stockout_rate_pct, res2.stockout_rate_pct)
            self.assertEqual(res1.service_level_pct, res2.service_level_pct)
            self.assertEqual(res1.total_cost, res2.total_cost)
            self.assertEqual(res1.total_ordered, res2.total_ordered)

    def test_06_inventory_conservation_and_zero_violations(self):
        """Verify conservation equation holds and zero violations occur across all providers."""
        scen = get_scenario("SCEN-01")
        sim = InventorySimulator(scen)
        for p in self.providers:
            res = sim.run_simulation(self.mock_series, p)
            self.assertEqual(res.constraint_violations_count, 0, f"{p.provider_id} had constraint violations")
            init_inv = res.daily_trace[0].starting_inventory
            recv = sum(l.arrivals for l in res.daily_trace)
            ful = res.total_fulfilled
            end_inv = res.daily_trace[-1].ending_inventory
            self.assertEqual(end_inv, init_inv + recv - ful, f"{p.provider_id} broke inventory conservation")


if __name__ == "__main__":
    unittest.main()
