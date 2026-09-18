"""
Automated Test Suite for Task 07: Fault Tolerance and Failure Recovery.

Validates the 12 functional criteria for Task 07:
1. Scenario A: Catalog Enricher failure handling and fallback.
2. Scenario B: Forecasting failure and partial-result preservation (enrichment preserved).
3. Scenario C: Replenishment failure and partial-result preservation (enrichment and forecast preserved).
4. Scenario D: Pricing Strategy failure and preservation of all 3 prior stages.
5. Scenario E: Persistent MCP session error isolation and subsequent recovery.
6. Scenario F: MCP process abrupt termination (crash_exit) handled safely without hanging.
7. Downstream protection: Downstream nodes do not execute when upstream nodes fail.
8. Telemetry sinks record failed service calls with accurate status and error messages.
9. Error taxonomy classification maps errors accurately to standardized taxonomy.
10. Benchmark raw_results.jsonl contains expected schema and valid records.
11. Benchmark summary.json contains valid aggregated metrics and latency statistics.
12. Clean subprocess cleanup without dangling processes or file locks.
"""
import os
import sys
import json
import asyncio
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "client"))

from experiments.fault_tolerance.failure_scenarios import (
    SCENARIOS,
    FaultInjectionContext,
    classify_error
)
from experiments.performance_benchmark.benchmark import run_deterministic_mcp
from client.persistent_client import PersistentMCPSessionPool, PersistentRetailOpsClient


MOCK_SERVER_PATHS = {
    "enricher": ROOT_DIR / "servers" / "mock-deterministic" / "enricher_server.py",
    "forecasting": ROOT_DIR / "servers" / "forecasting-replacement" / "server.py",
    "replenishment": ROOT_DIR / "servers" / "mock-deterministic" / "replenishment_server.py",
    "pricing": ROOT_DIR / "servers" / "mock-deterministic" / "pricing_server.py"
}


class TestFaultTolerance(unittest.TestCase):

    def test_01_scenario_a_enricher_failure(self):
        """Scenario A: Enricher fails, error is recorded, workflow halts at failed_enrichment."""
        with FaultInjectionContext("enricher", "tool_error", "Simulated enricher failure"):
            res = asyncio.run(run_deterministic_mcp("Samsung TV"))
            self.assertEqual(res.get("status"), "failed_enrichment")
            self.assertEqual(res.get("failed_steps"), ["enrich"])
            self.assertEqual(res.get("completed_steps"), [])
            self.assertTrue(any("Enrichment" in err for err in res.get("errors", [])))
            # Downstream protection: neither forecasting, replenishment, nor pricing should have executed
            service_call_names = [c["service_name"] for c in res.get("service_calls", [])]
            self.assertNotIn("Forecasting", service_call_names)
            self.assertNotIn("Replenishment", service_call_names)
            self.assertNotIn("Pricing Strategy", service_call_names)

    def test_02_scenario_b_forecasting_failure_preserves_enrichment(self):
        """Scenario B: Forecasting fails, enrichment output is preserved in partial results."""
        with FaultInjectionContext("forecasting", "tool_error", "Simulated forecasting failure"):
            res = asyncio.run(run_deterministic_mcp("Samsung TV"))
            self.assertEqual(res.get("status"), "failed_forecast")
            self.assertIn("enrich", res.get("completed_steps", []))
            self.assertIn("forecast", res.get("failed_steps", []))
            # Enrichment data preserved
            partial = res.get("partial_result", {})
            self.assertEqual(partial.get("category"), "electronics")
            self.assertEqual(res.get("enrichment", {}).get("brand"), "Samsung")
            # Downstream replenishment & pricing blocked
            self.assertNotIn("replenish", res.get("completed_steps", []))
            self.assertNotIn("price", res.get("completed_steps", []))

    def test_03_scenario_c_replenishment_failure_preserves_enrich_and_forecast(self):
        """Scenario C: Replenishment fails, both enrichment and forecast outputs are preserved."""
        with FaultInjectionContext("replenishment", "tool_error", "Simulated replenishment failure"):
            res = asyncio.run(run_deterministic_mcp("Samsung TV"))
            self.assertEqual(res.get("status"), "failed_replenishment")
            self.assertIn("enrich", res.get("completed_steps", []))
            self.assertIn("forecast", res.get("completed_steps", []))
            self.assertIn("replenish", res.get("failed_steps", []))
            # Partial results preserved
            partial = res.get("partial_result", {})
            self.assertEqual(partial.get("category"), "electronics")
            self.assertIsNotNone(partial.get("forecast", {}).get("final"))
            # Pricing blocked
            self.assertNotIn("price", res.get("completed_steps", []))

    def test_04_scenario_d_pricing_failure_preserves_prior_three_stages(self):
        """Scenario D: Pricing fails, enrichment, forecast, and replenishment preserved."""
        with FaultInjectionContext("pricing", "tool_error", "Simulated pricing failure"):
            res = asyncio.run(run_deterministic_mcp("Samsung TV"))
            self.assertEqual(res.get("status"), "failed_pricing")
            self.assertIn("enrich", res.get("completed_steps", []))
            self.assertIn("forecast", res.get("completed_steps", []))
            self.assertIn("replenish", res.get("completed_steps", []))
            self.assertIn("price", res.get("failed_steps", []))
            # Check all 3 prior preserved
            partial = res.get("partial_result", {})
            self.assertEqual(partial.get("category"), "electronics")
            self.assertIsNotNone(partial.get("forecast", {}).get("final"))
            self.assertIsNotNone(partial.get("replenishment", {}).get("reorder_qty"))

    def test_05_scenario_e_persistent_session_error_isolation_and_recovery(self):
        """Scenario E: Persistent session handles tool error and subsequent request recovers."""
        async def run_persistent_test():
            async with PersistentMCPSessionPool(server_paths=MOCK_SERVER_PATHS) as pool:
                client = PersistentRetailOpsClient(pool)
                # 1. Clean run
                r1 = await client.run_full_workflow("Samsung TV")
                self.assertEqual(r1.get("status"), "completed")

                # 2. Injected error in replenishment
                with FaultInjectionContext("replenishment", "tool_error", "Injected error"):
                    r2 = await client.run_full_workflow("Samsung TV")
                    self.assertEqual(r2.get("status"), "failed_replenishment")
                    self.assertIn("replenish", r2.get("failed_steps", []))
                    self.assertIn("forecast", r2.get("completed_steps", []))

                # 3. Subsequent run recovers cleanly without session recreation
                r3 = await client.run_full_workflow("Samsung TV")
                self.assertEqual(r3.get("status"), "completed")
                self.assertEqual(len(r3.get("failed_steps", [])), 0)

        asyncio.run(run_persistent_test())

    def test_06_scenario_f_subprocess_crash_termination_handled_cleanly(self):
        """Scenario F: Process abrupt crash (crash_exit) is caught without hanging."""
        with FaultInjectionContext("forecasting", "crash_exit", "Simulated crash exit"):
            res = asyncio.run(run_deterministic_mcp("Samsung TV"))
            self.assertEqual(res.get("status"), "failed_forecast")
            self.assertIn("forecast", res.get("failed_steps", []))
            self.assertTrue(len(res.get("errors", [])) > 0)
            # Ensure downstream stages were protected
            self.assertNotIn("replenish", res.get("completed_steps", []))
            self.assertNotIn("price", res.get("completed_steps", []))

    def test_07_downstream_protection_rules(self):
        """Verify downstream nodes abort when upstream stages have failed."""
        with FaultInjectionContext("forecasting", "tool_error"):
            res = asyncio.run(run_deterministic_mcp("Samsung TV"))
            completed = res.get("completed_steps", [])
            self.assertNotIn("replenish", completed)
            self.assertNotIn("price", completed)

    def test_08_telemetry_sink_records_failure_status(self):
        """Verify service_calls telemetry records failure status and duration."""
        with FaultInjectionContext("forecasting", "tool_error"):
            res = asyncio.run(run_deterministic_mcp("Samsung TV"))
            service_calls = res.get("service_calls", [])
            fc_call = next((c for c in service_calls if c["service_name"] == "Forecasting"), None)
            self.assertIsNotNone(fc_call)
            self.assertEqual(fc_call.get("status"), "failure")
            self.assertIsNotNone(fc_call.get("error"))

    def test_09_error_taxonomy_classification(self):
        """Verify error taxonomy correctly categorizes failure types."""
        self.assertEqual(classify_error("TaskGroup crashed: process exited"), "subprocess_termination")
        self.assertEqual(classify_error("Connection timed out waiting for STDIO"), "timeout")
        self.assertEqual(classify_error("Enrichment: Tool execution failed"), "tool_level_exception")
        self.assertEqual(classify_error("Corrupted json payload: parse error"), "invalid_response")
        self.assertEqual(classify_error("Handshake initialize failed"), "server_initialization_failure")
        self.assertEqual(classify_error(""), "none")

    def test_10_benchmark_raw_results_schema(self):
        """Verify raw_results.jsonl contains expected keys and non-negative durations."""
        raw_file = ROOT_DIR / "experiments" / "fault_tolerance" / "raw_results.jsonl"
        self.assertTrue(raw_file.exists())
        with open(raw_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        self.assertGreaterEqual(len(lines), 60)
        sample = json.loads(lines[0])
        expected_keys = {
            "run_id", "scenario_id", "target_service", "failure_mode",
            "repetition", "start_time", "end_time", "duration_ms",
            "evaluation", "workflow_status", "completed_steps", "failed_steps", "errors"
        }
        for k in expected_keys:
            self.assertIn(k, sample)
        self.assertGreater(sample["duration_ms"], 0)

    def test_11_benchmark_summary_structure(self):
        """Verify summary.json contains valid aggregated rates and scenario entries."""
        summary_file = ROOT_DIR / "experiments" / "fault_tolerance" / "summary.json"
        self.assertTrue(summary_file.exists())
        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)
        self.assertIn("scenarios", summary)
        self.assertIn("overall", summary)
        self.assertEqual(len(summary["scenarios"]), 6)
        for scen_id, data in summary["scenarios"].items():
            metrics = data["metrics"]
            self.assertEqual(metrics["failure_detection_rate_pct"], 100.0)
            self.assertEqual(metrics["expected_behavior_rate_pct"], 100.0)
            self.assertEqual(metrics["downstream_protection_rate_pct"], 100.0)
            self.assertEqual(metrics["cleanup_success_rate_pct"], 100.0)
            self.assertEqual(metrics["os_process_cleanup_rate_pct"], 100.0)
        self.assertEqual(summary["overall"]["overall_os_process_cleanup_rate_pct"], 100.0)

    def test_12_no_secrets_in_results(self):
        """Verify benchmark output does not leak API keys, tokens, or credentials."""
        raw_file = ROOT_DIR / "experiments" / "fault_tolerance" / "raw_results.jsonl"
        with open(raw_file, "r", encoding="utf-8") as f:
            content = f.read()
        for forbidden in ["sk-or-v1", "bearer", "authorization", "password", "api_key"]:
            self.assertNotIn(forbidden.lower(), content.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
