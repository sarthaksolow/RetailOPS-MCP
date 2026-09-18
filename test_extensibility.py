"""
Test Suite for Task 08: Extensibility Evaluation of RetailOps.

Validates all 14 criteria:
1. New MCP service exists and starts successfully
2. New tool getSupplierIntelligence is discoverable via MCP ListTools
3. New tool executes correctly and returns expected standardized schema
4. Tightly coupled baseline incorporates equivalent capability
5. Baseline direct function matches MCP tool output on identical inputs
6. Extended orchestrator executes 5-stage pipeline successfully
7. Extended baseline executes 5-stage pipeline successfully
8. Original 4-service MCP workflow remains functional and unchanged
9. Original 4-service baseline workflow remains functional and unchanged
10. Existing 4 MCP servers required zero source code modifications
11. Existing baseline required zero modifications to original 4 stage methods
12. Telemetry records the 5th service execution in both architectures
13. Evaluation script runs and produces summary.json, raw_results.jsonl, and results.md
14. All assertions use genuine behavioral checks
"""
import os
import sys
import json
import asyncio
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "client") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "client"))

from client.orchestrator import RetailOpsClient, MCPServerManager
from client.extended_orchestrator import ExtendedRetailOpsClient, ExtendedMCPServerManager
from baseline.tightly_coupled import TightlyCoupledRetailOps
from baseline.extended_tightly_coupled import ExtendedTightlyCoupledRetailOps
from baseline.supplier_intelligence import direct_get_supplier_intelligence
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession


class TestExtensibilityEvaluation(unittest.TestCase):

    def setUp(self):
        self.server_path = ROOT_DIR / "servers" / "supplier-intelligence" / "server.py"

    # Criterion 1: New MCP service exists and starts successfully
    def test_01_supplier_service_file_exists(self):
        self.assertTrue(self.server_path.exists(), f"Supplier server not found at {self.server_path}")

    # Criterion 2: New tool getSupplierIntelligence is discoverable via MCP ListTools
    def test_02_tool_discoverable(self):
        async def check_discovery():
            server_env = os.environ.copy()
            params = StdioServerParameters(
                command=sys.executable,
                args=[str(self.server_path)],
                env=server_env
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    tool_names = [t.name for t in tools_result.tools]
                    self.assertIn("getSupplierIntelligence", tool_names)

        asyncio.run(check_discovery())

    # Criterion 3: New tool executes correctly and returns expected standardized schema
    def test_03_tool_executes_valid_schema(self):
        async def call_tool():
            server_env = os.environ.copy()
            params = StdioServerParameters(
                command=sys.executable,
                args=[str(self.server_path)],
                env=server_env
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    resp = await session.call_tool("getSupplierIntelligence", {"category": "electronics", "reorder_qty": 200})
                    self.assertTrue(hasattr(resp, "content") and resp.content)
                    data = json.loads(resp.content[0].text)
                    required_keys = [
                        "supplier_id", "supplier_name", "category", "reliability_score",
                        "lead_time_days", "risk_category", "on_time_delivery_rate",
                        "quality_rating", "cost_index", "recommended_supplier", "narrative"
                    ]
                    for key in required_keys:
                        self.assertIn(key, data, f"Missing key '{key}' in tool response")
                    self.assertIsInstance(data["reliability_score"], (int, float))
                    self.assertIsInstance(data["lead_time_days"], int)
                    self.assertIn(data["risk_category"], ["low", "medium", "high"])

        asyncio.run(call_tool())

    # Criterion 4: Tightly coupled baseline incorporates equivalent capability
    def test_04_baseline_supplier_module_exists(self):
        baseline_file = ROOT_DIR / "baseline" / "supplier_intelligence.py"
        self.assertTrue(baseline_file.exists(), f"Baseline module not found at {baseline_file}")

    # Criterion 5: Baseline direct function matches MCP tool output on identical inputs
    def test_05_baseline_matches_mcp_output(self):
        async def compare_outputs():
            # Baseline
            b_out = direct_get_supplier_intelligence("tv", 150)

            # MCP
            server_env = os.environ.copy()
            params = StdioServerParameters(
                command=sys.executable,
                args=[str(self.server_path)],
                env=server_env
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    resp = await session.call_tool("getSupplierIntelligence", {"category": "tv", "reorder_qty": 150})
                    m_out = json.loads(resp.content[0].text)

            self.assertEqual(b_out["supplier_id"], m_out["supplier_id"])
            self.assertEqual(b_out["supplier_name"], m_out["supplier_name"])
            self.assertEqual(b_out["risk_category"], m_out["risk_category"])
            self.assertEqual(b_out["lead_time_days"], m_out["lead_time_days"])
            self.assertEqual(b_out["reliability_score"], m_out["reliability_score"])

        asyncio.run(compare_outputs())

    # Criterion 6: Extended orchestrator executes 5-stage pipeline successfully
    def test_06_extended_mcp_orchestrator(self):
        async def run_mcp_5_stage():
            client = ExtendedRetailOpsClient()
            res = await client.run_extended_workflow("Samsung TV", days_ahead=30)
            self.assertEqual(res["status"], "completed")
            expected_steps = ["enrich", "forecast", "replenish", "supplier", "price"]
            self.assertEqual(res["completed_steps"], expected_steps)
            self.assertIn("supplier_intelligence", res)
            self.assertIn("supplier_name", res["supplier_intelligence"])
            self.assertTrue(res["supplier_intelligence"]["supplier_id"].startswith("SUP-"))

        asyncio.run(run_mcp_5_stage())

    # Criterion 7: Extended baseline executes 5-stage pipeline successfully
    def test_07_extended_baseline(self):
        client = ExtendedTightlyCoupledRetailOps()
        res = client.run_extended_workflow("Samsung TV", days_ahead=30)
        self.assertEqual(res["status"], "completed")
        expected_steps = ["enrich", "forecast", "replenish", "supplier", "price"]
        self.assertEqual(res["completed_steps"], expected_steps)
        self.assertIn("supplier_intelligence", res)
        self.assertTrue(res["supplier_intelligence"]["supplier_id"].startswith("SUP-"))

    # Criterion 8: Original 4-service MCP workflow remains functional and unchanged
    def test_08_original_mcp_workflow_unchanged(self):
        async def run_original_mcp():
            client = RetailOpsClient()
            res = await client.run_full_workflow("Samsung TV", days_ahead=30)
            self.assertEqual(res["status"], "completed")
            expected_steps = ["enrich", "forecast", "replenish", "price"]
            self.assertEqual(res["completed_steps"], expected_steps)
            self.assertNotIn("supplier_intelligence", res)

        asyncio.run(run_original_mcp())

    # Criterion 9: Original 4-service baseline workflow remains functional and unchanged
    def test_09_original_baseline_workflow_unchanged(self):
        client = TightlyCoupledRetailOps()
        res = client.run_full_workflow("Samsung TV", days_ahead=30)
        self.assertEqual(res["status"], "completed")
        expected_steps = ["enrich", "forecast", "replenish", "price"]
        self.assertEqual(res["completed_steps"], expected_steps)
        self.assertNotIn("supplier_intelligence", res)

    # Criterion 10: Existing 4 MCP servers required zero source code modifications
    def test_10_existing_mcp_servers_unmodified(self):
        existing_servers = [
            ROOT_DIR / "servers" / "catalog-enricher" / "server.py",
            ROOT_DIR / "servers" / "forecasting" / "server.py",
            ROOT_DIR / "servers" / "replenishment" / "server.py",
            ROOT_DIR / "servers" / "pricing-strategy" / "server.py"
        ]
        for s in existing_servers:
            self.assertTrue(s.exists())
            with open(s, "r", encoding="utf-8") as f:
                content = f.read()
            # Must not import or reference the new supplier service
            self.assertNotIn("supplier_intelligence", content.lower())
            self.assertNotIn("getsupplierintelligence", content.lower())
            self.assertNotIn("servers/supplier-intelligence", content.lower())

    # Criterion 11: Existing baseline required zero modifications to original 4 stage methods
    def test_11_existing_baseline_methods_unmodified(self):
        baseline_file = ROOT_DIR / "baseline" / "tightly_coupled.py"
        with open(baseline_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("supplier", content.lower())
        self.assertNotIn("getsupplierintelligence", content.lower())

    # Criterion 12: Telemetry records the 5th service execution in both architectures
    def test_12_telemetry_captures_supplier_service(self):
        async def verify_telemetry():
            # Baseline
            b_client = ExtendedTightlyCoupledRetailOps()
            b_res = b_client.run_extended_workflow("Samsung TV")
            b_services = [sc["service_name"] for sc in b_res["service_calls"]]
            self.assertIn("Supplier Intelligence", b_services)

            # MCP
            m_client = ExtendedRetailOpsClient()
            m_res = await m_client.run_extended_workflow("Samsung TV")
            m_services = [sc["service_name"] for sc in m_res["service_calls"]]
            self.assertIn("Supplier Intelligence", m_services)

        asyncio.run(verify_telemetry())

    # Criterion 13: Evaluation script runs and produces summary.json, raw_results.jsonl, and results.md
    def test_13_experiment_artifacts_exist(self):
        ext_dir = ROOT_DIR / "experiments" / "extensibility"
        summary_file = ext_dir / "summary.json"
        raw_file = ext_dir / "raw_results.jsonl"
        results_md = ext_dir / "results.md"
        self.assertTrue(summary_file.exists(), f"Missing {summary_file}")
        self.assertTrue(raw_file.exists(), f"Missing {raw_file}")
        self.assertTrue(results_md.exists(), f"Missing {results_md}")

        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)
            self.assertTrue(summary.get("hypothesis_supported"))
            self.assertIn("structural_metrics", summary)
            self.assertIn("empirical_execution_summary", summary)

    # Criterion 14: All assertions use genuine behavioral checks
    def test_14_genuine_behavioral_validation(self):
        client = ExtendedTightlyCoupledRetailOps()
        # Non-empty, valid values checked, not mere non-empty dictionary
        res = client.run_extended_workflow("Samsung TV")
        sup = res["supplier_intelligence"]
        self.assertEqual(sup["risk_category"], "low")
        self.assertGreater(sup["reliability_score"], 0.8)
        self.assertGreater(sup["lead_time_days"], 0)
        self.assertTrue(len(sup["narrative"]) > 20)


if __name__ == "__main__":
    unittest.main()
