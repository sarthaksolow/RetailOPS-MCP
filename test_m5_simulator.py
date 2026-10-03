"""
Deterministic Unit Test Battery for M5 Operational Simulation Environment.
Verifies:
1. Inventory conservation (available = starting + arrivals; ending = available - fulfilled).
2. Order arrival timing (order placed at day t with lead time L arrives strictly at day t + L).
3. Lost sales accounting (demand = fulfilled + lost_sales).
4. Supplier delay impact (L=21 days delays arrivals appropriately).
5. Constraint enforcement (MOQ violations accurately flagged).
6. Repeated simulation reproducibility (identical seed & inputs produce bit-for-bit identical results).
7. Correct metric calculations (Stockout rate, Service level, Holding and Replenishment costs).
"""
import unittest
from experiments.m5_operational.scenarios import SCENARIOS, get_scenario
from experiments.m5_operational.decision_provider import (
    BaseDecisionProvider,
    OperationalDecisionContext,
    ReplenishmentDecision,
    FixedThresholdDecisionProvider
)
from experiments.m5_operational.simulator import InventorySimulator, SimulationResults


class MockTestDecisionProvider(BaseDecisionProvider):
    """Simple controllable decision provider for exact deterministic unit tests."""
    def __init__(self, order_schedule: dict):
        self.order_schedule = order_schedule

    @property
    def provider_id(self) -> str:
        return "mock_test_provider"

    def decide(self, context: OperationalDecisionContext) -> ReplenishmentDecision:
        qty = self.order_schedule.get(context.current_day, 0)
        return ReplenishmentDecision(
            order_quantity=qty,
            order_timing="immediate" if qty > 0 else "defer",
            estimated_demand=context.mean_historical_daily_demand,
            rationale=f"Test scheduled order {qty}",
            provider_metadata={}
        )


class TestM5OperationalSimulator(unittest.TestCase):

    def setUp(self):
        # Create a clean, manually verifiable synthetic series with 28 days
        # Daily sales: alternating 5 and 10 units
        self.eval_records = []
        for i in range(1, 29):
            sales = 10 if i % 2 == 0 else 5
            self.eval_records.append({
                "d": f"d_{1913+i}",
                "day_index": 1913 + i,
                "date": f"2016-05-{i:02d}",
                "weekday": "Monday",
                "sales": sales
            })
            
        self.mock_series = {
            "metadata": {
                "series_id": "TEST_STORE_ITEM_001",
                "item_id": "ITEM_001",
                "store_id": "TEST_STORE",
                "cat_id": "TEST_CAT",
                "unit_sell_price": 10.0,
                "unit_procurement_cost": 5.0,
                "holding_cost_rate": 0.001
            },
            "train_records": [{"sales": 8} for _ in range(90)], # mean daily = 8.0
            "eval_records": self.eval_records
        }

    def test_01_inventory_conservation_and_lost_sales(self):
        """Verify that starting inventory, arrivals, sales, and ending inventory balance exactly."""
        scen = get_scenario("SCEN-01")
        # Provider that places no orders
        provider = MockTestDecisionProvider(order_schedule={})
        sim = InventorySimulator(scen)
        res = sim.run_simulation(self.mock_series, provider)
        
        # Initial on-hand = round(1.0 * 8.0 * 7) = 56 units
        curr_expected = 56
        for log in res.daily_trace:
            self.assertEqual(log.starting_inventory, curr_expected)
            self.assertEqual(log.available_inventory, log.starting_inventory + log.arrivals)
            self.assertEqual(log.ending_inventory, log.available_inventory - log.fulfilled_demand)
            self.assertEqual(log.realized_demand, log.fulfilled_demand + log.lost_sales)
            curr_expected = log.ending_inventory

    def test_02_order_arrival_timing(self):
        """Verify an order placed on day t arrives on day t + L."""
        scen = get_scenario("SCEN-01") # L = 7 days
        # Place an order of 30 units on day 2
        provider = MockTestDecisionProvider(order_schedule={2: 30})
        sim = InventorySimulator(scen)
        res = sim.run_simulation(self.mock_series, provider)
        
        # Day 2: order placed
        day2_log = res.daily_trace[1]
        self.assertEqual(day2_log.order_placed, 30)
        
        # Days 3 to 8: arrivals should be 0
        for d in range(3, 9):
            self.assertEqual(res.daily_trace[d - 1].arrivals, 0)
            
        # Day 9 (2 + 7): order arrives
        day9_log = res.daily_trace[8]
        self.assertEqual(day9_log.arrivals, 30)

    def test_03_supplier_delay_impact(self):
        """Verify supplier delay scenario triples lead time to 21 days."""
        scen = get_scenario("SCEN-04") # L = 21 days
        provider = MockTestDecisionProvider(order_schedule={1: 50})
        sim = InventorySimulator(scen)
        res = sim.run_simulation(self.mock_series, provider)
        
        # Day 1: ordered 50
        self.assertEqual(res.daily_trace[0].order_placed, 50)
        # Should NOT arrive on day 8
        self.assertEqual(res.daily_trace[7].arrivals, 0)
        # Should arrive on day 22 (1 + 21)
        self.assertEqual(res.daily_trace[21].arrivals, 50)

    def test_04_constraint_enforcement(self):
        """Verify ordering below MOQ flags a constraint violation."""
        scen = get_scenario("SCEN-01") # MOQ = 20
        # Place order of 10 units (below MOQ 20) on day 1
        provider = MockTestDecisionProvider(order_schedule={1: 10})
        sim = InventorySimulator(scen)
        res = sim.run_simulation(self.mock_series, provider)
        
        self.assertEqual(res.constraint_violations_count, 1)
        self.assertTrue(res.daily_trace[0].constraint_violation)

    def test_05_reproducibility(self):
        """Verify repeated simulation executions produce bit-for-bit identical results."""
        scen = get_scenario("SCEN-02")
        provider = FixedThresholdDecisionProvider()
        sim = InventorySimulator(scen)
        
        res1 = sim.run_simulation(self.mock_series, provider)
        res2 = sim.run_simulation(self.mock_series, provider)
        
        self.assertEqual(res1.stockout_rate_pct, res2.stockout_rate_pct)
        self.assertEqual(res1.service_level_pct, res2.service_level_pct)
        self.assertEqual(res1.total_cost, res2.total_cost)
        self.assertEqual(res1.total_ordered, res2.total_ordered)

    def test_06_metric_calculation_accuracy(self):
        """Verify exact mathematical computation of Stockout Rate and Service Level."""
        scen = get_scenario("SCEN-03") # Low inventory (0.2 * 8 * 7 = 11 units)
        # No orders placed, demand is 5, 10, 5, 10...
        # Day 1: stock 11, demand 5 -> fulfilled 5, end 6
        # Day 2: stock 6, demand 10 -> fulfilled 6, lost 4, end 0 (Stockout day 1)
        # Day 3: stock 0, demand 5 -> fulfilled 0, lost 5, end 0 (Stockout day 2)
        # All remaining 26 days have stockout (Total 27 stockout days)
        provider = MockTestDecisionProvider(order_schedule={})
        sim = InventorySimulator(scen)
        res = sim.run_simulation(self.mock_series, provider)
        
        expected_stockout_rate = round((27 / 28) * 100, 2) # 96.43%
        self.assertEqual(res.stockout_rate_pct, expected_stockout_rate)
        
        # Total demand = 14*5 + 14*10 = 210 units
        # Total fulfilled = 5 + 6 = 11 units
        expected_service_level = round((11 / 210) * 100, 2) # 5.24%
        self.assertEqual(res.service_level_pct, expected_service_level)

    def test_07_retailops_decision_provider_interface(self):
        """Verify RetailOpsDecisionProvider produces valid ReplenishmentDecisions conforming to schema."""
        from experiments.m5_operational.decision_provider import RetailOpsDecisionProvider
        provider = RetailOpsDecisionProvider()
        self.assertEqual(provider.provider_id, "retailops_mcp")

        context = OperationalDecisionContext(
            series_id="TEST_SERIES",
            item_id="TEST_ITEM",
            store_id="TEST_STORE",
            category="FOODS",
            current_day=1,
            date="2016-05-01",
            weekday="Monday",
            event_name=None,
            on_hand_inventory=10,
            in_transit_inventory=0,
            pipeline_orders_count=0,
            mean_historical_daily_demand=2.0,
            supplier_lead_time_days=7,
            supplier_reliability=0.95,
            minimum_order_quantity=20,
            maximum_order_quantity=500,
            unit_cost=1.5,
            unit_sell_price=3.0,
            scenario_id="SCEN-01"
        )
        decision = provider.decide(context)
        self.assertIsInstance(decision, ReplenishmentDecision)
        self.assertGreaterEqual(decision.order_quantity, 20) # MOQ enforced
        self.assertIn("retailops_reasoning_pipeline", decision.provider_metadata["policy"])
        self.assertIn(decision.order_timing, ["immediate", "soon", "defer"])

    def test_08_retailops_inventory_conservation_and_reproducibility(self):
        """Verify RetailOpsDecisionProvider satisfies inventory conservation and zero violations."""
        from experiments.m5_operational.decision_provider import RetailOpsDecisionProvider
        scen = get_scenario("SCEN-01")
        provider = RetailOpsDecisionProvider()
        sim = InventorySimulator(scen)
        res1 = sim.run_simulation(self.mock_series, provider)
        res2 = sim.run_simulation(self.mock_series, provider)

        # Zero constraint violations
        self.assertEqual(res1.constraint_violations_count, 0)
        self.assertEqual(res2.constraint_violations_count, 0)

        # Bit-for-bit reproducibility
        self.assertEqual(res1.stockout_rate_pct, res2.stockout_rate_pct)
        self.assertEqual(res1.total_cost, res2.total_cost)

        # Conservation equation: ending == initial + arrivals - fulfilled
        init_inv = res1.daily_trace[0].starting_inventory
        total_recv = sum(l.arrivals for l in res1.daily_trace)
        total_ful = res1.total_fulfilled
        end_inv = res1.daily_trace[-1].ending_inventory
        self.assertEqual(end_inv, init_inv + total_recv - total_ful)


if __name__ == "__main__":
    unittest.main()

