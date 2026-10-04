"""
Automated Unit and Regression Test Suite for Step 10 Revision:
Controlled Cross-Architecture Service Replacement & Modularity Experiment.

Verifies:
1. All four replacement decision providers inherit from BaseDecisionProvider.
2. Identical OperationalDecisionContext can be evaluated by every replaced provider.
3. Every provider produces valid ReplenishmentDecision satisfying common schema.
4. WorkflowLLM generative plan executes updated statistical operation step cleanly.
5. Bit-for-bit deterministic reproducibility across repeated runs.
6. Zero supplier constraint violations (MOQ and max order quantity bounds respected).
7. Predefined Replacement Burden Index formula matches exported results.json values.
"""
import unittest
import json
from pathlib import Path

from experiments.m5_operational.decision_provider import (
    BaseDecisionProvider,
    OperationalDecisionContext,
    ReplenishmentDecision,
)
from experiments.replacement_modularity_comparison.replacements.retailops import (
    RetailOpsStatisticalReplacementProvider
)
from experiments.replacement_modularity_comparison.replacements.flowr import (
    FlowrStatisticalReplacementProvider
)
from experiments.replacement_modularity_comparison.replacements.workflowllm import (
    WorkflowLLMStatisticalReplacementProvider
)
from experiments.replacement_modularity_comparison.replacements.agentic_replenishment import (
    AgenticStatisticalReplacementProvider
)
from experiments.replacement_modularity_comparison.run_experiment import (
    calculate_replacement_burden_index
)

ROOT_DIR = Path(__file__).resolve().parent


class TestCrossArchitectureServiceReplacement(unittest.TestCase):

    def setUp(self):
        self.providers = [
            RetailOpsStatisticalReplacementProvider(),
            FlowrStatisticalReplacementProvider(),
            WorkflowLLMStatisticalReplacementProvider(),
            AgenticStatisticalReplacementProvider()
        ]

        self.sample_context = OperationalDecisionContext(
            series_id="CA_1_FOODS_1_004",
            item_id="FOODS_1_004",
            store_id="CA_1",
            category="FOODS",
            current_day=7,
            date="2016-05-01",
            weekday="Sunday",
            event_name=None,
            on_hand_inventory=12,
            in_transit_inventory=25,
            pipeline_orders_count=1,
            mean_historical_daily_demand=4.2,
            supplier_lead_time_days=7,
            supplier_reliability=0.95,
            minimum_order_quantity=20,
            maximum_order_quantity=500,
            unit_cost=1.18,
            unit_sell_price=1.96,
            scenario_id="SCEN-01"
        )

    def test_01_all_providers_inherit_base_decision_provider(self):
        """Verify inheritance and interface contract across all 4 replaced architectures."""
        for provider in self.providers:
            self.assertIsInstance(
                provider,
                BaseDecisionProvider,
                f"{provider.__class__.__name__} must inherit from BaseDecisionProvider"
            )
            self.assertIsInstance(provider.provider_id, str)
            self.assertTrue(len(provider.provider_id) > 0)

    def test_02_all_providers_produce_valid_replenishment_decisions(self):
        """Verify each provider returns a compliant ReplenishmentDecision object."""
        for provider in self.providers:
            dec = provider.decide(self.sample_context)
            self.assertIsInstance(dec, ReplenishmentDecision)
            self.assertIsInstance(dec.order_quantity, int)
            self.assertGreaterEqual(dec.order_quantity, 0)
            self.assertIn(dec.order_timing, ("immediate", "soon", "defer"))
            self.assertIsInstance(dec.estimated_demand, (int, float))
            self.assertGreaterEqual(dec.estimated_demand, 0.0)
            self.assertIsInstance(dec.rationale, str)
            self.assertTrue(len(dec.rationale) > 10)
            self.assertIsInstance(dec.provider_metadata, dict)

    def test_03_supplier_constraint_enforcement(self):
        """Verify MOQ and maximum capacity constraints are enforced by all architectures."""
        low_stock_context = OperationalDecisionContext(
            series_id="CA_1_FOODS_1_004",
            item_id="FOODS_1_004",
            store_id="CA_1",
            category="FOODS",
            current_day=7,
            date="2016-05-01",
            weekday="Sunday",
            event_name=None,
            on_hand_inventory=2,
            in_transit_inventory=0,
            pipeline_orders_count=0,
            mean_historical_daily_demand=10.0,
            supplier_lead_time_days=5,
            supplier_reliability=0.95,
            minimum_order_quantity=50,
            maximum_order_quantity=200,
            unit_cost=2.00,
            unit_sell_price=4.00,
            scenario_id="SCEN-03"
        )

        for provider in self.providers:
            dec = provider.decide(low_stock_context)
            if dec.order_quantity > 0:
                self.assertGreaterEqual(
                    dec.order_quantity,
                    low_stock_context.minimum_order_quantity,
                    f"{provider.provider_id} violated MOQ bound"
                )
                self.assertLessEqual(
                    dec.order_quantity,
                    low_stock_context.maximum_order_quantity,
                    f"{provider.provider_id} violated maximum capacity bound"
                )

    def test_04_workflowllm_plan_execution_trace(self):
        """Verify WorkflowLLM executes the updated statistical plan step."""
        provider = WorkflowLLMStatisticalReplacementProvider()
        dec = provider.decide(self.sample_context)
        meta = dec.provider_metadata
        self.assertIn("generated_plan_steps", meta)
        self.assertIn("statistical_demand_forecast", meta["generated_plan_steps"])
        self.assertEqual(len(meta["generated_plan_steps"]), 6)

    def test_05_deterministic_reproducibility(self):
        """Verify identical contexts yield bit-for-bit identical decisions across all providers."""
        for provider in self.providers:
            dec1 = provider.decide(self.sample_context)
            dec2 = provider.decide(self.sample_context)
            self.assertEqual(dec1.order_quantity, dec2.order_quantity)
            self.assertEqual(dec1.order_timing, dec2.order_timing)
            self.assertEqual(dec1.estimated_demand, dec2.estimated_demand)
            self.assertEqual(dec1.rationale, dec2.rationale)

    def test_06_replacement_burden_index_consistency(self):
        """Verify composite RBI formula aligns with exported results.json values."""
        results_path = ROOT_DIR / "experiments" / "replacement_modularity_comparison" / "results.json"
        self.assertTrue(results_path.exists(), "results.json must exist")

        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        measurements = data["modularity_measurements"]
        for arch_id, metrics in measurements.items():
            expected_rbi = calculate_replacement_burden_index(metrics)
            self.assertEqual(
                metrics["replacement_burden_index"],
                expected_rbi,
                f"RBI calculation mismatch for {arch_id}"
            )

        # RetailOps must have lowest RBI among all 4 evaluated architectures
        retailops_rbi = measurements["retailops_mcp"]["replacement_burden_index"]
        for arch_id, metrics in measurements.items():
            if arch_id != "retailops_mcp":
                self.assertLess(
                    retailops_rbi,
                    metrics["replacement_burden_index"],
                    f"RetailOps RBI ({retailops_rbi}) should be lower than {arch_id} ({metrics['replacement_burden_index']})"
                )


if __name__ == "__main__":
    unittest.main()
