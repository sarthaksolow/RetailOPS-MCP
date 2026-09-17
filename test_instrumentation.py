"""
Unit and Mock Tests for RetailOps Research Instrumentation.
Verifies telemetry generation, service timings, error recording, log sanitization, and JSONL serialization.
"""
import sys
import json
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Add client to path
sys.path.insert(0, str(Path(__file__).parent / "client"))

from client.telemetry import (
    ServiceCallTelemetry,
    ExecutionTelemetry,
    TelemetryLogger,
    now_iso
)
from client.orchestrator import RetailOpsClient, RetailOpsState


def test_telemetry_models():
    """Verify ExecutionTelemetry and ServiceCallTelemetry models and dict conversion."""
    print("1️⃣ Testing telemetry dataclasses...")
    sc = ServiceCallTelemetry(
        service_name="Forecasting",
        tool_name="getForecast",
        start_time=now_iso(),
        end_time=now_iso(),
        duration_ms=125.5,
        status="success"
    )
    d = sc.to_dict()
    assert d["service_name"] == "Forecasting"
    assert d["tool_name"] == "getForecast"
    assert d["duration_ms"] >= 0
    assert d["status"] == "success"
    assert d["error"] is None

    exec_telem = ExecutionTelemetry(
        execution_id="exec-test-1234",
        workflow_name="retail_operations_orchestrator",
        product_name="Test TV",
        category="electronics",
        start_time=now_iso(),
        end_time=now_iso(),
        total_duration_ms=450.2,
        workflow_status="completed",
        completed_steps=["enrich", "forecast", "replenish", "price"],
        failed_steps=[],
        service_calls=[d],
        partial_result={"category": "electronics"},
        errors=[]
    )
    ed = exec_telem.to_dict()
    assert ed["execution_id"] == "exec-test-1234"
    assert ed["workflow_name"] == "retail_operations_orchestrator"
    assert ed["total_duration_ms"] >= 0
    assert len(ed["service_calls"]) == 1
    assert ed["completed_steps"] == ["enrich", "forecast", "replenish", "price"]
    print("   ✅ PASSED: Dataclasses work as expected")


def test_logger_and_sanitization():
    """Verify TelemetryLogger writes valid JSON lines and scrubs sensitive keys."""
    print("2️⃣ Testing logger sanitization and JSONL persistence...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        log_file = Path(tmp_dir) / "test_telemetry.jsonl"
        logger = TelemetryLogger(log_file=log_file)

        raw_telem = ExecutionTelemetry(
            execution_id="exec-sec-9999",
            workflow_name="test_workflow",
            product_name="Secure Laptop",
            category="electronics",
            start_time=now_iso(),
            end_time=now_iso(),
            total_duration_ms=250.0,
            workflow_status="completed",
            completed_steps=["enrich"],
            failed_steps=[],
            service_calls=[{
                "service_name": "Catalog Enricher",
                "api_key": "sk-secret-token-12345",
                "auth_token": "bearer-sensitive-data",
                "duration_ms": 100.0,
                "status": "success"
            }],
            partial_result={"password_hash": "sensitive123"},
            errors=[]
        )

        logger.log_execution(raw_telem)

        # Assert file exists and is parseable JSON
        assert log_file.exists(), "Log file was not created"
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1, f"Expected 1 line, got {len(lines)}"

        parsed = json.loads(lines[0])
        assert parsed["execution_id"] == "exec-sec-9999"

        # Check sanitization
        service_call = parsed["service_calls"][0]
        assert service_call["api_key"] == "[REDACTED]", "api_key was not redacted"
        assert service_call["auth_token"] == "[REDACTED]", "auth_token was not redacted"
        assert parsed["partial_result"]["password_hash"] == "[REDACTED]", "password_hash was not redacted"
    print("   ✅ PASSED: Secrets are redacted and logs are valid JSON")


async def test_mocked_workflow_instrumentation():
    """Verify execution_id, start/end times, durations, and steps during a mocked client workflow."""
    print("3️⃣ Testing RetailOpsClient workflow telemetry with mocks...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        log_file = Path(tmp_dir) / "workflow_telemetry.jsonl"
        logger = TelemetryLogger(log_file=log_file)
        client = RetailOpsClient(telemetry_logger=logger)

        # Mock all 4 server calls
        mock_enrich = {
            "category": "electronics",
            "brand": "Samsung",
            "description": "Smart TV",
            "alternatives": [],
            "narrative": "Enriched successfully"
        }
        mock_forecast = {
            "category": "electronics",
            "base_forecast": 100.0,
            "final_forecast": 150.0,
            "seasonal_multiplier": 1.5,
            "event": "Diwali",
            "narrative": "Good forecast"
        }
        mock_replenish = {
            "reorder_qty": 50,
            "reorder_timing": "soon",
            "stockout_risk": "low",
            "narrative": "Order soon"
        }
        mock_price = {
            "category": "electronics",
            "current_price": 25000.0,
            "recommended_price": 24000.0,
            "price_change_pct": -4.0,
            "recommendation_type": "competitive",
            "narrative": "Slight discount"
        }

        async def fake_enrich(product_name, telemetry_sink=None):
            if telemetry_sink is not None:
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Catalog Enricher",
                    tool_name="enrichProduct",
                    start_time=now_iso(),
                    end_time=now_iso(),
                    duration_ms=45.0,
                    status="success"
                ).to_dict())
            return mock_enrich

        async def fake_forecast(category, days_ahead=30, telemetry_sink=None):
            if telemetry_sink is not None:
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Forecasting",
                    tool_name="getForecast",
                    start_time=now_iso(),
                    end_time=now_iso(),
                    duration_ms=30.0,
                    status="success"
                ).to_dict())
            return mock_forecast

        async def fake_replenish(forecast_data, current_stock=None, in_transit=None, telemetry_sink=None):
            if telemetry_sink is not None:
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Replenishment",
                    tool_name="getReplenishmentDecision",
                    start_time=now_iso(),
                    end_time=now_iso(),
                    duration_ms=25.0,
                    status="success"
                ).to_dict())
            return mock_replenish

        async def fake_pricing(category, forecasted_demand, inventory_level=None, current_price=None, telemetry_sink=None):
            if telemetry_sink is not None:
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Pricing Strategy",
                    tool_name="getPricingStrategy",
                    start_time=now_iso(),
                    end_time=now_iso(),
                    duration_ms=20.0,
                    status="success"
                ).to_dict())
            return mock_price

        with patch("client.orchestrator.server_manager.call_enrichment", side_effect=fake_enrich), \
             patch("client.orchestrator.server_manager.call_forecasting", side_effect=fake_forecast), \
             patch("client.orchestrator.server_manager.call_replenishment", side_effect=fake_replenish), \
             patch("client.orchestrator.server_manager.call_pricing", side_effect=fake_pricing):

            result = await client.run_full_workflow("Samsung TV", days_ahead=30)

            # Check return structure
            assert result["status"] == "completed"
            assert result["execution_id"].startswith("exec-")
            assert result["total_duration_ms"] >= 0
            assert "start_time" in result
            assert "end_time" in result
            assert result["completed_steps"] == ["enrich", "forecast", "replenish", "price"]
            assert result["failed_steps"] == []
            assert len(result["service_calls"]) == 4

            # Check JSON line logged
            with open(log_file, "r", encoding="utf-8") as f:
                logs = [json.loads(line) for line in f]
            assert len(logs) == 1
            entry = logs[0]
            assert entry["execution_id"] == result["execution_id"]
            assert entry["workflow_status"] == "completed"
            assert len(entry["service_calls"]) == 4
    print("   ✅ PASSED: Mocked full workflow telemetry correctly populated and logged")


async def test_mocked_workflow_failure():
    """Verify failed service calls record status, error message, and failed_steps."""
    print("4️⃣ Testing RetailOpsClient failure telemetry with mocks...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        log_file = Path(tmp_dir) / "fail_telemetry.jsonl"
        logger = TelemetryLogger(log_file=log_file)
        client = RetailOpsClient(telemetry_logger=logger)

        async def fake_enrich_fail(product_name, telemetry_sink=None):
            err = "Simulated catalog enrichment failure"
            if telemetry_sink is not None:
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Catalog Enricher",
                    tool_name="enrichProduct",
                    start_time=now_iso(),
                    end_time=now_iso(),
                    duration_ms=15.0,
                    status="failure",
                    error=err
                ).to_dict())
            return {"error": err}

        async def fake_forecast_fail(category, days_ahead=30, telemetry_sink=None):
            err = "No data found for category 'general'"
            if telemetry_sink is not None:
                telemetry_sink.append(ServiceCallTelemetry(
                    service_name="Forecasting",
                    tool_name="getForecast",
                    start_time=now_iso(),
                    end_time=now_iso(),
                    duration_ms=10.0,
                    status="failure",
                    error=err
                ).to_dict())
            return {"error": err}

        with patch("client.orchestrator.server_manager.call_enrichment", side_effect=fake_enrich_fail), \
             patch("client.orchestrator.server_manager.call_forecasting", side_effect=fake_forecast_fail):

            result = await client.run_full_workflow("Unknown Widget", days_ahead=30)
            assert result["status"] == "failed_forecast"
            assert "enrich" in result["failed_steps"]
            assert "forecast" in result["failed_steps"]
            assert len(result["errors"]) >= 1

            with open(log_file, "r", encoding="utf-8") as f:
                logs = [json.loads(line) for line in f]
            assert len(logs) == 1
            assert logs[0]["workflow_status"] == "failed_forecast"
            assert logs[0]["failed_steps"] == ["enrich", "forecast"]
    print("   ✅ PASSED: Failure telemetry captured correctly")


def main():
    print("\n" + "="*70)
    print("🧪 RUNNING INSTRUMENTATION TEST SUITE")
    print("="*70 + "\n")
    test_telemetry_models()
    test_logger_and_sanitization()
    asyncio.run(test_mocked_workflow_instrumentation())
    asyncio.run(test_mocked_workflow_failure())
    print("\n" + "="*70)
    print("🎉 ALL INSTRUMENTATION TESTS PASSED!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
