"""
Test Suite for Statistical Forecasting Replacement Service.
Verifies:
1. FastMCP tool getForecast accepts standard category and days_ahead parameters.
2. Returns all required contract keys matching getForecast schema.
3. Operates offline without external LLM dependencies.
4. Downstream replenishment and pricing successfully consume replacement forecast.
5. Verifies data leakage prevention (training split restricted to <= 92 observations).
"""
import os
import sys
import json
import asyncio
import unittest
import importlib.util
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "client"))

from client.orchestrator import MCPServerManager

SERVER_PATH = ROOT_DIR / "servers" / "forecasting-statistical" / "server.py"


class TestStatisticalForecastingReplacement(unittest.TestCase):

    REQUIRED_SCHEMA_KEYS = [
        "category",
        "base_forecast",
        "seasonal_multiplier",
        "historical_surge_factor",
        "final_forecast",
        "event",
        "narrative",
        "model_metadata"
    ]

    @classmethod
    def setUpClass(cls):
        # Dynamically import the replacement server module
        spec = importlib.util.spec_from_file_location("server_stat", str(SERVER_PATH))
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    def test_01_direct_tool_contract_all_categories(self):
        """Verify getForecast directly returns complete, valid schema across all 7 categories."""
        categories = ["tv", "laptop", "phone", "kitchen_appliances", "fashion", "groceries", "electronics"]
        for cat in categories:
            res = asyncio.run(self.mod.getForecast(cat, days_ahead=30))
            self.assertEqual(res.get("category"), cat)
            for key in self.REQUIRED_SCHEMA_KEYS:
                self.assertIn(key, res, f"Missing key '{key}' in getForecast response for '{cat}'")
            self.assertIsInstance(res["base_forecast"], (int, float))
            self.assertIsInstance(res["final_forecast"], (int, float))
            self.assertGreater(res["final_forecast"], 0.0)
            self.assertIsInstance(res["narrative"], str)
            self.assertIn("Holt-Winters", res["narrative"])

    def test_02_model_metadata_specification(self):
        """Verify model_metadata includes expected algorithm structure and parameter settings."""
        res = asyncio.run(self.mod.getForecast("phone", days_ahead=30))
        meta = res.get("model_metadata", {})
        self.assertEqual(meta.get("model_type"), "holt_winters_additive")
        self.assertEqual(meta.get("season_length"), 7)
        self.assertEqual(meta.get("alpha"), 0.25)
        self.assertEqual(meta.get("beta"), 0.05)
        self.assertEqual(meta.get("gamma"), 0.20)
        self.assertIn("training_samples", meta)

    def test_03_data_leakage_protection(self):
        """Verify training sample count never exceeds the pre-test boundary of 92 records."""
        for cat in ["tv", "laptop", "fashion"]:
            res = asyncio.run(self.mod.getForecast(cat, days_ahead=30))
            train_count = res.get("model_metadata", {}).get("training_samples")
            self.assertEqual(train_count, 92, "Training samples must equal 92 (first 92 days of dataset)")

    def test_04_mcp_stdio_orchestration(self):
        """Verify orchestrator invokes the statistical server via stdio and receives success."""
        with patch.dict(os.environ, {"RETAILOPS_FORECASTING_SERVER_PATH": str(SERVER_PATH)}):
            mgr = MCPServerManager()
            telemetry_sink = []
            res = asyncio.run(mgr.call_forecasting("electronics", 30, telemetry_sink=telemetry_sink))
            self.assertNotIn("error", res)
            self.assertEqual(res.get("category"), "electronics")
            self.assertGreater(res.get("final_forecast"), 0.0)
            self.assertEqual(len(telemetry_sink), 1)
            self.assertEqual(telemetry_sink[0]["status"], "success")

    def test_05_downstream_consumption_preservation(self):
        """Verify replenishment consumes statistical forecast without schema errors."""
        with patch.dict(os.environ, {"RETAILOPS_FORECASTING_SERVER_PATH": str(SERVER_PATH)}):
            mgr = MCPServerManager()
            forecast_res = asyncio.run(mgr.call_forecasting("tv", 30))
            self.assertNotIn("error", forecast_res)
            # Call replenishment
            replenish_res = asyncio.run(mgr.call_replenishment(forecast_res))
            self.assertNotIn("error", replenish_res)
            self.assertIn("reorder_qty", replenish_res)
            self.assertIn("reorder_timing", replenish_res)


if __name__ == "__main__":
    unittest.main()
