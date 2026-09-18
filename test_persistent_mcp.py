"""
Automated unit and regression test suite for Task 06:
Persistent MCP Server and Process-Lifecycle Overhead Analysis.

Tests:
1. Persistent server pool starts successfully.
2. Multiple tool calls reuse the same session.
3. Repeated calls produce valid results.
4. Results preserve expected output schema and parity.
5. Independent workflows do not leak state.
6. Sessions and subprocesses close correctly.
7. Tool-call failures do not leave orphaned processes or break subsequent calls.
8. Invalid inputs are handled safely.
9. Persistent execution preserves replenishment and pricing behavior.
10. No secrets or API keys are written into benchmark records or telemetry.
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

from client.persistent_client import PersistentMCPSessionPool, PersistentRetailOpsClient
from baseline.tightly_coupled import TightlyCoupledRetailOps
from baseline.replacement.forecasting_replacement import replacement_direct_get_forecast
from client.telemetry import TelemetryLogger


class TestPersistentMCP(unittest.IsolatedAsyncioTestCase):

    @classmethod
    def setUpClass(cls):
        # Configure deterministic local mock servers
        cls.mock_paths = {
            "enricher": ROOT_DIR / "servers" / "mock-deterministic" / "enricher_server.py",
            "forecasting": ROOT_DIR / "servers" / "forecasting-replacement" / "server.py",
            "replenishment": ROOT_DIR / "servers" / "mock-deterministic" / "replenishment_server.py",
            "pricing": ROOT_DIR / "servers" / "mock-deterministic" / "pricing_server.py"
        }
        cls.baseline = TightlyCoupledRetailOps(forecasting_service=replacement_direct_get_forecast)

    async def test_01_persistent_server_starts_successfully(self):
        """Verify persistent server pool starts all 4 servers and records startup timing."""
        pool = PersistentMCPSessionPool(server_paths=self.mock_paths)
        timing = await pool.start()
        try:
            self.assertTrue(pool.is_connected)
            self.assertEqual(len(pool.sessions), 4)
            for sname in ["enricher", "forecasting", "replenishment", "pricing"]:
                self.assertIn(sname, pool.sessions)
                self.assertIn(sname, timing)
                self.assertGreater(timing[sname]["total_startup_ms"], 0)
        finally:
            await pool.close()
            self.assertFalse(pool.is_connected)

    async def test_02_multiple_tool_calls_reuse_same_session(self):
        """Verify multiple calls are serviced across the same long-lived session."""
        async with PersistentMCPSessionPool(server_paths=self.mock_paths) as pool:
            # 3 sequential calls to enricher session
            res1 = await pool.call_tool_on_session("enricher", "enrichProduct", {"input": {"product_name": "Samsung TV", "product_data": {}}})
            res2 = await pool.call_tool_on_session("enricher", "enrichProduct", {"input": {"product_name": "Dell XPS Laptop", "product_data": {}}})
            res3 = await pool.call_tool_on_session("enricher", "enrichProduct", {"input": {"product_name": "Apple iPhone 15", "product_data": {}}})

            self.assertEqual(res1.get("category"), "electronics")
            self.assertEqual(res2.get("category"), "electronics")
            self.assertEqual(res3.get("category"), "electronics")

    async def test_03_repeated_calls_produce_valid_results(self):
        """Verify repeated executions through PersistentRetailOpsClient succeed consistently."""
        async with PersistentMCPSessionPool(server_paths=self.mock_paths) as pool:
            client = PersistentRetailOpsClient(pool)
            for prod in ["Samsung TV", "Dell XPS Laptop", "Apple iPhone 15"]:
                res = await client.run_full_workflow(prod, days_ahead=30)
                self.assertEqual(res["status"], "completed")
                self.assertEqual(res["completed_steps"], ["enrich", "forecast", "replenish", "price"])
                self.assertEqual(res["failed_steps"], [])
                self.assertGreater(res["forecast"]["final"], 0)
                self.assertGreater(res["replenishment"]["reorder_qty"], 0)
                self.assertGreater(res["pricing"]["recommended_price"], 0)

    async def test_04_results_preserve_expected_output_schema(self):
        """Verify output schema of PersistentRetailOpsClient matches standard contract."""
        async with PersistentMCPSessionPool(server_paths=self.mock_paths) as pool:
            client = PersistentRetailOpsClient(pool)
            res = await client.run_full_workflow("Samsung TV", days_ahead=30)

            required_top_keys = {
                "execution_id", "workflow_name", "start_time", "end_time",
                "total_duration_ms", "completed_steps", "failed_steps",
                "service_calls", "product_name", "category", "timestamp",
                "status", "enrichment", "forecast", "replenishment", "pricing",
                "errors", "architecture", "partial_result"
            }
            for k in required_top_keys:
                self.assertIn(k, res)

            self.assertEqual(res["architecture"], "persistent_mcp")
            self.assertEqual(len(res["service_calls"]), 4)

    async def test_05_independent_workflows_do_not_leak_state(self):
        """Verify subsequent workflow executions with different products maintain isolated states."""
        async with PersistentMCPSessionPool(server_paths=self.mock_paths) as pool:
            client = PersistentRetailOpsClient(pool)
            res1 = await client.run_full_workflow("Samsung TV", days_ahead=30)
            res2 = await client.run_full_workflow("Dell XPS Laptop", days_ahead=30)

            self.assertNotEqual(res1["execution_id"], res2["execution_id"])
            self.assertEqual(res1["product_name"], "Samsung TV")
            self.assertEqual(res2["product_name"], "Dell XPS Laptop")
            self.assertEqual(res1["enrichment"]["brand"], "Samsung")
            self.assertEqual(res2["enrichment"]["brand"], "Dell")

    async def test_06_sessions_and_subprocesses_close_correctly(self):
        """Verify sessions and underlying stdio pipes close cleanly and measure shutdown timing."""
        pool = PersistentMCPSessionPool(server_paths=self.mock_paths)
        await pool.start()
        self.assertTrue(pool.is_connected)
        shutdown_ms = await pool.close()
        self.assertFalse(pool.is_connected)
        self.assertEqual(len(pool.sessions), 0)
        self.assertGreaterEqual(shutdown_ms, 0)

    async def test_07_tool_call_failures_do_not_corrupt_subsequent_calls(self):
        """Verify error in one tool invocation does not crash the session pool or prevent next call."""
        async with PersistentMCPSessionPool(server_paths=self.mock_paths) as pool:
            client = PersistentRetailOpsClient(pool)
            # Call with unmapped/bad product (graceful general fallback)
            res_bad = await client.run_full_workflow("NonExistentProductUnknown123", days_ahead=30)
            self.assertIn(res_bad["status"], ["completed", "failed_forecast"])

            # Subsequent call with known product still succeeds cleanly
            res_good = await client.run_full_workflow("Samsung TV", days_ahead=30)
            self.assertEqual(res_good["status"], "completed")

    async def test_08_invalid_inputs_handled_safely(self):
        """Verify calling a non-existent tool or bad server raises predictable error."""
        async with PersistentMCPSessionPool(server_paths=self.mock_paths) as pool:
            with self.assertRaises(RuntimeError):
                await pool.call_tool_on_session("non_existent_server", "dummyTool", {})

    async def test_09_persistent_execution_preserves_business_parity(self):
        """Verify deterministic domain calculations match the tightly coupled baseline."""
        async with PersistentMCPSessionPool(server_paths=self.mock_paths) as pool:
            client = PersistentRetailOpsClient(pool)
            mcp_res = await client.run_full_workflow("Samsung TV", days_ahead=30)
            tc_res = self.baseline.run_full_workflow("Samsung TV", days_ahead=30)

            self.assertEqual(mcp_res["category"], tc_res["category"])
            self.assertEqual(mcp_res["replenishment"]["reorder_qty"], tc_res["replenishment"]["reorder_qty"])
            self.assertAlmostEqual(mcp_res["pricing"]["recommended_price"], tc_res["pricing"]["recommended_price"], places=1)

    async def test_10_no_secrets_in_benchmark_records(self):
        """Verify API keys and credentials are never captured in results or telemetry."""
        pool = PersistentMCPSessionPool(server_paths=self.mock_paths)
        await pool.start()
        try:
            client = PersistentRetailOpsClient(pool)
            res = await client.run_full_workflow("Samsung TV", days_ahead=30)
            json_str = json.dumps(res)
            self.assertNotIn("sk-or-v1-", json_str)
            self.assertNotIn("Bearer ", json_str)
        finally:
            await pool.close()


if __name__ == "__main__":
    unittest.main()
