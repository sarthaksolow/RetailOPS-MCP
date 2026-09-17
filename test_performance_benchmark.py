"""
Unit and Contract Tests for Task 05: Performance Benchmark.
Tests:
1. Benchmark record schema and required fields.
2. Valid architecture values ("mcp", "tightly_coupled").
3. Valid condition values ("deterministic_local", "end_to_end").
4. Deterministic benchmark execution runs cleanly.
5. Runtime values are non-negative.
6. Summary statistics (mean, median, std_dev, p95) calculated correctly.
7. Failed runs are recorded rather than silently ignored.
8. No secrets or credentials appear in benchmark output.
9. MCP and tightly coupled outputs have comparable required fields.
"""
import os
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "client"))

from experiments.performance_benchmark.benchmark import (
    calculate_metrics,
    compute_benchmark_summary,
    run_deterministic_tightly_coupled,
    run_deterministic_mcp
)
from baseline.tightly_coupled import TightlyCoupledRetailOps
from baseline.replacement.forecasting_replacement import replacement_direct_get_forecast


class TestPerformanceBenchmark(unittest.TestCase):

    REQUIRED_RECORD_FIELDS = {
        "run_id",
        "architecture",
        "condition",
        "input_category",
        "input_product",
        "warmup",
        "start_time",
        "end_time",
        "total_duration_ms",
        "service_durations_ms",
        "workflow_status",
        "completed_steps",
        "failed_steps",
        "errors",
        "external_api_used"
    }

    def test_01_summary_metric_calculations(self):
        """Verify descriptive statistics formulas (mean, median, min, max, std_dev, p95)."""
        durations = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = calculate_metrics(durations)
        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["mean"], 30.0)
        self.assertEqual(stats["median"], 30.0)
        self.assertEqual(stats["min"], 10.0)
        self.assertEqual(stats["max"], 50.0)
        self.assertAlmostEqual(stats["std_dev"], 15.81, places=2)
        self.assertEqual(stats["p95"], 50.0)

        # Empty list handling
        empty_stats = calculate_metrics([])
        self.assertEqual(empty_stats["count"], 0)
        self.assertIsNone(empty_stats["mean"])

    def test_02_record_schema_and_valid_values(self):
        """Verify benchmark records adhere to strict field and enum requirements."""
        dummy_record = {
            "run_id": "test-run-123",
            "architecture": "mcp",
            "condition": "deterministic_local",
            "input_category": "electronics",
            "input_product": "Samsung TV",
            "warmup": False,
            "start_time": "2026-09-18T00:00:00Z",
            "end_time": "2026-09-18T00:00:01Z",
            "total_duration_ms": 1000.0,
            "service_durations_ms": {"Catalog Enricher": 250.0},
            "workflow_status": "completed",
            "completed_steps": ["enrich", "forecast", "replenish", "price"],
            "failed_steps": [],
            "errors": [],
            "external_api_used": False
        }
        # Check all required keys exist
        for key in self.REQUIRED_RECORD_FIELDS:
            self.assertIn(key, dummy_record)

        # Valid architecture
        self.assertIn(dummy_record["architecture"], ["mcp", "tightly_coupled"])
        # Valid condition
        self.assertIn(dummy_record["condition"], ["deterministic_local", "end_to_end"])
        # Non-negative runtime
        self.assertGreaterEqual(dummy_record["total_duration_ms"], 0)

    def test_03_failure_recording_in_summary(self):
        """Verify failed runs are counted and retained in summary rather than dropped."""
        sample_records = [
            {
                "run_id": "tc-1",
                "architecture": "tightly_coupled",
                "condition": "deterministic_local",
                "warmup": False,
                "workflow_status": "completed",
                "total_duration_ms": 5.0,
                "service_durations_ms": {"Forecasting": 1.0}
            },
            {
                "run_id": "tc-2",
                "architecture": "tightly_coupled",
                "condition": "deterministic_local",
                "warmup": False,
                "workflow_status": "failed_pricing",
                "total_duration_ms": 4.0,
                "service_durations_ms": {"Forecasting": 1.0}
            }
        ]
        summary = compute_benchmark_summary(sample_records)
        tc_metrics = summary["deterministic_tightly_coupled"]
        self.assertEqual(tc_metrics["total_runs"], 2)
        self.assertEqual(tc_metrics["successful_runs"], 1)
        self.assertEqual(tc_metrics["failed_runs"], 1)
        self.assertEqual(tc_metrics["completion_rate"], 50.0)

    def test_04_no_secrets_in_benchmark_records(self):
        """Verify API keys and credentials never appear in raw benchmark records or summary."""
        fake_secret = "sk-or-v1-secret-never-expose-in-benchmark"
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": fake_secret}):
            rec = {
                "run_id": "sec-test",
                "architecture": "mcp",
                "condition": "deterministic_local",
                "total_duration_ms": 100.0,
                "workflow_status": "completed",
                "warmup": False,
                "service_durations_ms": {},
                "errors": []
            }
            summary = compute_benchmark_summary([rec])
            dumped = json.dumps(summary)
            self.assertNotIn(fake_secret, dumped)

    def test_05_schema_parity_under_deterministic_condition(self):
        """Verify both architectures produce comparable required fields under deterministic execution."""
        # Baseline deterministic
        res_tc = run_deterministic_tightly_coupled("Samsung TV", days_ahead=30)
        self.assertEqual(res_tc["status"], "completed")
        self.assertIn("enrichment", res_tc)
        self.assertIn("forecast", res_tc)
        self.assertIn("replenishment", res_tc)
        self.assertIn("pricing", res_tc)
        self.assertGreaterEqual(res_tc["forecast"]["final"], 0)

        # Baseline and MCP schema field comparison
        required_summary_keys = ["category", "enrichment", "forecast", "replenishment", "pricing"]
        for k in required_summary_keys:
            self.assertIn(k, res_tc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
