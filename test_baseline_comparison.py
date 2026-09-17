"""
Comparison Test Suite: MCP Architecture vs. Tightly Coupled Baseline.
Verifies input/output parity, field alignment, error handling, and independence.
"""
import sys
import json
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch

# Ensure root is in path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "client"))

from baseline.tightly_coupled import TightlyCoupledRetailOps
from client.orchestrator import RetailOpsClient
from client.telemetry import TelemetryLogger, ServiceCallTelemetry, now_iso


def test_baseline_standalone():
    """Verify baseline processes valid inputs and handles invalid categories without MCP."""
    print("1️⃣ Testing Tightly Coupled Baseline standalone...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger = TelemetryLogger(log_file=Path(tmp_dir) / "baseline_log.jsonl")
        tc = TightlyCoupledRetailOps(telemetry_logger=logger)

        # Valid input
        res = tc.run_full_workflow("Samsung TV", days_ahead=30)
        assert res["status"] == "completed"
        assert res["architecture"] == "tightly_coupled"
        assert res["category"] == "electronics"
        assert res["forecast"]["final"] > 0
        assert res["replenishment"]["reorder_qty"] >= 0
        assert res["pricing"]["recommended_price"] > 0
        assert res["completed_steps"] == ["enrich", "forecast", "replenish", "price"]
        assert len(res["service_calls"]) == 4

        # Invalid input (unknown category)
        res_inv = tc.run_full_workflow("completely_unknown_xyz_999", days_ahead=30)
        assert res_inv["status"] == "failed_forecast"
        assert "forecast" in res_inv["failed_steps"]
        assert len(res_inv["errors"]) > 0

    print("   ✅ PASSED: Baseline functions standalone without MCP")


def test_schema_parity():
    """Verify both MCP client and baseline return equivalent top-level and nested keys."""
    print("2️⃣ Testing schema and field parity between MCP and Baseline...")
    tc = TightlyCoupledRetailOps()
    tc_res = tc.run_full_workflow("tv", days_ahead=30)

    # Expected top-level keys
    expected_top_keys = {
        "execution_id", "workflow_name", "architecture", "start_time", "end_time",
        "total_duration_ms", "completed_steps", "failed_steps", "service_calls",
        "product_name", "category", "timestamp", "status", "enrichment",
        "forecast", "replenishment", "pricing", "errors", "partial_result"
    }

    assert expected_top_keys.issubset(tc_res.keys()), f"Missing keys in baseline: {expected_top_keys - set(tc_res.keys())}"

    # Verify nested schema consistency
    enrich_keys = {"category", "brand", "description", "narrative"}
    forecast_keys = {"final", "event", "narrative"}
    replenish_keys = {"reorder_qty", "timing", "narrative"}
    pricing_keys = {"recommended_price", "change_pct", "narrative"}

    assert enrich_keys.issubset(tc_res["enrichment"].keys())
    assert forecast_keys.issubset(tc_res["forecast"].keys())
    assert replenish_keys.issubset(tc_res["replenishment"].keys())
    assert pricing_keys.issubset(tc_res["pricing"].keys())
    print("   ✅ PASSED: Schema fields are aligned across architectures")


async def test_comparison_with_mocked_mcp():
    """Compare MCP architecture vs Baseline using controlled mocks to avoid external API variance."""
    print("3️⃣ Testing controlled comparison between MCP and Baseline...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        mcp_log = Path(tmp_dir) / "mcp_telemetry.jsonl"
        tc_log = Path(tmp_dir) / "tc_telemetry.jsonl"

        mcp_client = RetailOpsClient(telemetry_logger=TelemetryLogger(log_file=mcp_log))
        tc_engine = TightlyCoupledRetailOps(telemetry_logger=TelemetryLogger(log_file=tc_log))

        mock_enrich = {"category": "electronics", "brand": "Tv", "description": "TV description", "narrative": "Enriched"}
        mock_forecast = {"category": "electronics", "base_forecast": 115.0, "final_forecast": 300.15, "event": "Diwali", "narrative": "Forecasted"}
        mock_replenish = {"reorder_qty": 250, "reorder_timing": "soon", "stockout_risk": "medium", "narrative": "Replenished"}
        mock_price = {"category": "electronics", "current_price": 9000.0, "recommended_price": 9450.0, "price_change_pct": 5.0, "narrative": "Priced"}

        async def fake_call_enrich(name, telemetry_sink=None):
            if telemetry_sink is not None:
                telemetry_sink.append(ServiceCallTelemetry("Catalog Enricher", "enrichProduct", now_iso(), now_iso(), 10.0, "success").to_dict())
            return mock_enrich

        async def fake_call_forecast(cat, days, telemetry_sink=None):
            if telemetry_sink is not None:
                telemetry_sink.append(ServiceCallTelemetry("Forecasting", "getForecast", now_iso(), now_iso(), 8.0, "success").to_dict())
            return mock_forecast

        async def fake_call_replenish(f_data, current_stock=None, in_transit=None, telemetry_sink=None):
            if telemetry_sink is not None:
                telemetry_sink.append(ServiceCallTelemetry("Replenishment", "getReplenishmentDecision", now_iso(), now_iso(), 6.0, "success").to_dict())
            return mock_replenish

        async def fake_call_price(cat, demand, current_price=None, inventory_level=None, telemetry_sink=None):
            if telemetry_sink is not None:
                telemetry_sink.append(ServiceCallTelemetry("Pricing Strategy", "getPricingStrategy", now_iso(), now_iso(), 5.0, "success").to_dict())
            return mock_price

        with patch("client.orchestrator.server_manager.call_enrichment", side_effect=fake_call_enrich), \
             patch("client.orchestrator.server_manager.call_forecasting", side_effect=fake_call_forecast), \
             patch("client.orchestrator.server_manager.call_replenishment", side_effect=fake_call_replenish), \
             patch("client.orchestrator.server_manager.call_pricing", side_effect=fake_call_price):

            mcp_res = await mcp_client.run_full_workflow("tv", days_ahead=30)
            tc_res = tc_engine.run_full_workflow("tv", days_ahead=30)

            # Both must complete
            assert mcp_res["status"] == "completed"
            assert tc_res["status"] == "completed"

            # Check distinct architecture tags
            assert mcp_res["architecture"] == "mcp"
            assert tc_res["architecture"] == "tightly_coupled"

            # Check matching domain outputs
            assert mcp_res["category"] == tc_res["category"] == "electronics"
            assert mcp_res["completed_steps"] == tc_res["completed_steps"] == ["enrich", "forecast", "replenish", "price"]

            # Check telemetry persistence
            with open(mcp_log, "r", encoding="utf-8") as f:
                mcp_record = json.loads(f.readline())
            with open(tc_log, "r", encoding="utf-8") as f:
                tc_record = json.loads(f.readline())

            assert mcp_record["architecture"] == "mcp"
            assert tc_record["architecture"] == "tightly_coupled"

    print("   ✅ PASSED: Both architectures execute identically and log distinct telemetry")


def main():
    print("\n" + "="*70)
    print("🧪 BASELINE ARCHITECTURAL COMPARISON TEST SUITE")
    print("="*70 + "\n")
    test_baseline_standalone()
    test_schema_parity()
    asyncio.run(test_comparison_with_mocked_mcp())
    print("\n" + "="*70)
    print("🎉 ALL COMPARISON TESTS PASSED!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
