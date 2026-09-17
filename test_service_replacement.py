"""
Automated Test Suite for Task 04: Service Replacement Experiment.
Verifies:
1. Original MCP workflow remains functional.
2. Original tightly coupled workflow remains functional.
3. MCP replacement returns the required schema.
4. Tightly coupled replacement returns the required schema.
5. Replenishment and pricing consume replacement output successfully.
6. Original and replacement services can be selected independently.
7. Invalid replacement output is handled safely.
8. No API keys or secrets are written to logs or test output.
"""
import os
import sys
import json
import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Set encoding and root path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "client"))

from client.orchestrator import MCPServerManager, RetailOpsClient, RetailOpsState
from baseline.tightly_coupled import TightlyCoupledRetailOps
from baseline.replacement.forecasting_replacement import replacement_direct_get_forecast
from client.telemetry import TelemetryLogger


class TestServiceReplacement(unittest.TestCase):

    REQUIRED_SCHEMA_KEYS = {
        "category",
        "base_forecast",
        "seasonal_multiplier",
        "historical_surge_factor",
        "final_forecast",
        "event",
        "narrative"
    }

    def setUp(self):
        self.mgr = MCPServerManager()
        self.test_log_path = ROOT_DIR / "logs" / "test_replacement_telemetry.jsonl"
        if self.test_log_path.exists():
            self.test_log_path.unlink()
        self.logger = TelemetryLogger(log_file=self.test_log_path)

    def tearDown(self):
        if self.test_log_path.exists():
            self.test_log_path.unlink()

    # -------------------------------------------------------------
    # 1. Test Original MCP Workflow Remains Functional
    # -------------------------------------------------------------
    def test_01_original_mcp_workflow_functional(self):
        """Verify original MCP server parameters point to original forecasting server by default."""
        with patch.dict(os.environ, {}, clear=False):
            if "RETAILOPS_FORECASTING_SERVER_PATH" in os.environ:
                del os.environ["RETAILOPS_FORECASTING_SERVER_PATH"]
            mgr = MCPServerManager()
            forecast_server = str(mgr.servers["forecasting"])
            self.assertTrue(forecast_server.endswith(os.path.join("forecasting", "server.py")),
                            f"Expected original forecasting server path, got: {forecast_server}")
            self.assertTrue(mgr.servers["forecasting"].exists())

    # -------------------------------------------------------------
    # 2. Test Original Tightly Coupled Workflow Remains Functional
    # -------------------------------------------------------------
    def test_02_original_tightly_coupled_functional(self):
        """Verify original baseline runs with default in-memory forecasting."""
        tc = TightlyCoupledRetailOps(telemetry_logger=self.logger)
        result = tc.run_full_workflow("Samsung TV", days_ahead=30)
        self.assertEqual(result["status"], "completed")
        self.assertIn("forecast", result)
        self.assertIn("replenishment", result)
        self.assertIn("pricing", result)
        self.assertIsNotNone(result["forecast"].get("final"))
        # Verify tool_name in telemetry recorded direct_get_forecast
        forecast_calls = [c for c in result["service_calls"] if c["service_name"] == "Forecasting"]
        self.assertTrue(len(forecast_calls) >= 1)
        self.assertEqual(forecast_calls[0]["tool_name"], "direct_get_forecast")

    # -------------------------------------------------------------
    # 3. Test MCP Replacement Returns Required Schema
    # -------------------------------------------------------------
    def test_03_mcp_replacement_schema(self):
        """Test replacement MCP server directly or via server_manager returns required fields."""
        replacement_path = str(ROOT_DIR / "servers" / "forecasting-replacement" / "server.py")
        self.assertTrue(os.path.exists(replacement_path), f"Replacement server missing at {replacement_path}")

        with patch.dict(os.environ, {"RETAILOPS_FORECASTING_SERVER_PATH": replacement_path}):
            mgr = MCPServerManager()
            telemetry_sink = []
            result = asyncio.run(mgr.call_forecasting("electronics", 30, telemetry_sink=telemetry_sink))
            self.assertNotIn("error", result)
            for key in self.REQUIRED_SCHEMA_KEYS:
                self.assertIn(key, result, f"Missing key '{key}' in replacement MCP response")
            self.assertIsInstance(result["final_forecast"], (int, float))
            self.assertIsInstance(result["base_forecast"], (int, float))
            self.assertIsInstance(result["narrative"], str)
            self.assertIn("60-day MA", result["narrative"])

    # -------------------------------------------------------------
    # 4. Test Tightly Coupled Replacement Returns Required Schema
    # -------------------------------------------------------------
    def test_04_tightly_coupled_replacement_schema(self):
        """Test baseline replacement function returns all required schema fields."""
        tc = TightlyCoupledRetailOps(telemetry_logger=self.logger)
        result = replacement_direct_get_forecast(
            category="electronics",
            days_ahead=30,
            sales_df=tc.sales_df,
            events=tc.events,
            surge_profiles=tc.surge_profiles,
            moving_average_window=60
        )
        self.assertNotIn("error", result)
        for key in self.REQUIRED_SCHEMA_KEYS:
            self.assertIn(key, result, f"Missing key '{key}' in replacement baseline response")
        self.assertEqual(result["category"], "electronics")
        self.assertIsInstance(result["final_forecast"], (int, float))
        self.assertIn("60-day MA", result["narrative"])

    # -------------------------------------------------------------
    # 5. Test Downstream Replenishment & Pricing Consume Replacement Output
    # -------------------------------------------------------------
    def test_05_downstream_stages_consume_replacement_output(self):
        """Verify replenishment and pricing consume replacement forecast successfully."""
        tc = TightlyCoupledRetailOps(
            telemetry_logger=self.logger,
            forecasting_service=replacement_direct_get_forecast
        )
        result = tc.run_full_workflow("Samsung TV", days_ahead=30)
        self.assertEqual(result["status"], "completed")
        self.assertIn("replenishment", result)
        self.assertIn("pricing", result)
        self.assertGreater(result["replenishment"]["reorder_qty"], 0)
        self.assertGreater(result["pricing"]["recommended_price"], 0)

        # Check telemetry recorded replacement function name
        forecast_calls = [c for c in result["service_calls"] if c["service_name"] == "Forecasting"]
        self.assertEqual(forecast_calls[0]["tool_name"], "replacement_direct_get_forecast")

    # -------------------------------------------------------------
    # 6. Test Independent Selection of Original and Replacement Services
    # -------------------------------------------------------------
    def test_06_independent_selection(self):
        """Verify both architectures can toggle cleanly between original and replacement."""
        # Baseline toggle
        tc_default = TightlyCoupledRetailOps()
        self.assertIsNone(tc_default.forecasting_service)

        tc_custom = TightlyCoupledRetailOps(forecasting_service=replacement_direct_get_forecast)
        self.assertIsNotNone(tc_custom.forecasting_service)

        # MCP toggle
        with patch.dict(os.environ, {}, clear=False):
            if "RETAILOPS_FORECASTING_SERVER_PATH" in os.environ:
                del os.environ["RETAILOPS_FORECASTING_SERVER_PATH"]
            mgr_default = MCPServerManager()
            self.assertTrue(str(mgr_default.servers["forecasting"]).endswith(os.path.join("forecasting", "server.py")))

        repl_path = str(ROOT_DIR / "servers" / "forecasting-replacement" / "server.py")
        with patch.dict(os.environ, {"RETAILOPS_FORECASTING_SERVER_PATH": repl_path}):
            mgr_repl = MCPServerManager()
            self.assertTrue(str(mgr_repl.servers["forecasting"]).endswith(os.path.join("forecasting-replacement", "server.py")))

    # -------------------------------------------------------------
    # 7. Test Error Handling for Invalid Replacement Output
    # -------------------------------------------------------------
    def test_07_invalid_replacement_output_handling(self):
        """Verify orchestrator handles invalid output from replacement service gracefully."""
        # 1. Baseline handling with broken forecast return
        def broken_forecasting_service(*args, **kwargs):
            return {"error": "Simulated forecast algorithm failure."}

        tc_broken = TightlyCoupledRetailOps(
            telemetry_logger=self.logger,
            forecasting_service=broken_forecasting_service
        )
        res = tc_broken.run_full_workflow("Samsung TV")
        self.assertEqual(res["status"], "failed_forecast")
        self.assertIn("forecast", res["failed_steps"])

        # 2. Non-existent MCP replacement server path
        with patch.dict(os.environ, {"RETAILOPS_FORECASTING_SERVER_PATH": "non_existent_server.py"}):
            mgr_bad = MCPServerManager()
            telemetry_sink = []
            bad_res = asyncio.run(mgr_bad.call_forecasting("electronics", 30, telemetry_sink=telemetry_sink))
            self.assertIn("error", bad_res)
            self.assertEqual(telemetry_sink[0]["status"], "failure")

    # -------------------------------------------------------------
    # 8. Test Security: No Secrets Leaked in Logs or Test Output
    # -------------------------------------------------------------
    def test_08_no_secrets_in_logs_or_output(self):
        """Verify OpenRouter API key and tokens are never written to telemetry logs."""
        fake_secret = "sk-or-v1-secret-research-key-never-leak"
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": fake_secret}):
            tc = TightlyCoupledRetailOps(telemetry_logger=self.logger)
            tc.run_full_workflow("Samsung TV")

        # Inspect logged content
        if self.test_log_path.exists():
            with open(self.test_log_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertNotIn(fake_secret, content, "API secret leaked into telemetry log file!")

        # Verify .gitignore protects .env
        gitignore_path = ROOT_DIR / ".gitignore"
        self.assertTrue(gitignore_path.exists())
        with open(gitignore_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]
            self.assertIn(".env", lines)


if __name__ == "__main__":
    unittest.main(verbosity=2)
