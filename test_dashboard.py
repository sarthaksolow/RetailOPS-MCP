import unittest
from dashboard.app import app
from dashboard.domain import InventoryItem, Decision, ServiceStatus
from dashboard.services.inventory_service import InventoryService
from dashboard.services.decision_service import DecisionService
from dashboard.services.system_service import SystemService
from dashboard.services.metrics_service import MetricsService
from dashboard.layout import (
    render_sidebar,
    render_sidebar_nav_links,
    render_dashboard_view,
    render_inventory_view,
    render_decisions_view,
    render_copilot_view,
    render_services_view,
    render_evaluation_view,
)
from dashboard.services.mcp_client import MCPToolClient
from dashboard.services.llm_service import LLMService
from dashboard.services.chat_service import ChatService


class TestRetailOpsDashboard(unittest.TestCase):

    def setUp(self):
        self.inv_service = InventoryService()
        self.dec_service = DecisionService()
        self.sys_service = SystemService()
        self.met_service = MetricsService()
        self.mcp_client = MCPToolClient()
        self.llm_service = LLMService()
        self.chat_service = ChatService()

    def test_app_initialization(self):
        """Verifies Dash application and root layout are initialized."""
        self.assertIsNotNone(app)
        self.assertIsNotNone(app.layout)
        self.assertEqual(app.title, "RetailOps | MCP Decision Platform")

    def test_inventory_service(self):
        """Verifies inventory service produces valid InventoryItem instances."""
        items = self.inv_service.get_inventory_items()
        self.assertEqual(len(items), 5)
        for it in items:
            self.assertIsInstance(it, InventoryItem)
            self.assertGreater(it.daily_demand, 0)
            self.assertIn(it.stockout_risk, ["low", "medium", "high"])
            self.assertGreaterEqual(it.recommended_order, 0)

    def test_decision_service_lifecycle(self):
        """Verifies replenishment proposals can be approved and overridden."""
        decisions = self.dec_service.get_all_decisions()
        self.assertGreater(len(decisions), 0)
        target_id = decisions[0].id

        # Approve
        approved = self.dec_service.approve_decision(target_id)
        self.assertIsNotNone(approved)
        self.assertEqual(approved.status, "Approved")
        self.assertEqual(approved.operator_action, "APPROVE")

        # Override
        overridden = self.dec_service.override_decision(target_id, 35, "Tempered by operator")
        self.assertIsNotNone(overridden)
        self.assertEqual(overridden.final_qty, 35)
        self.assertEqual(overridden.status, "Overridden")
        self.assertEqual(overridden.operator_action, "OVERRIDE")

    def test_system_service(self):
        """Verifies system service discovers all 5 MCP servers."""
        services = self.sys_service.get_service_statuses()
        self.assertEqual(len(services), 5)
        service_names = [s.name for s in services]
        self.assertIn("Catalog Enricher", service_names)
        self.assertIn("Forecasting", service_names)
        self.assertIn("Replenishment", service_names)
        self.assertIn("Pricing Strategy", service_names)
        self.assertIn("Supplier Intelligence", service_names)
        for s in services:
            self.assertIsInstance(s, ServiceStatus)
            self.assertGreater(s.tool_count, 0)
            self.assertGreater(s.latency_ms, 0)

    def test_metrics_service(self):
        """Verifies metrics service reads empirical final evaluation results."""
        kpis = self.met_service.get_dashboard_kpis()
        self.assertEqual(len(kpis), 4)

        fc = self.met_service.get_forecasting_metrics()
        self.assertIn("aggregate_accuracy", fc)

        m5 = self.met_service.get_m5_metrics()
        self.assertIn("retailops_mcp", m5)

        arch = self.met_service.get_architecture_metrics()
        self.assertIn("overall_comparison", arch)

        hitl = self.met_service.get_hitl_metrics()
        self.assertIn("modes_summary", hitl)

    def test_mcp_tool_client(self):
        """Verifies standardized MCP tool dispatching returns structured payloads and latency."""
        # 1. Inventory status
        res1 = self.mcp_client.call_tool("servers/replenishment", "get_inventory_status", {})
        self.assertIn("result", res1)
        self.assertIn("high_risk_items", res1["result"])
        self.assertGreaterEqual(res1["latency_ms"], 0)

        # 2. Forecasting
        res2 = self.mcp_client.call_tool("servers/forecasting", "get_forecast", {"category": "FOODS"})
        self.assertIn("baseline_daily_forecast", res2["result"])

        # 3. Replenishment calculation
        res3 = self.mcp_client.call_tool("servers/replenishment", "calculate_replenishment", {"series_id": "CA_1_FOODS_1_004"})
        self.assertIn("recommended_reorder_qty", res3["result"])

        # 4. Supplier status
        res4 = self.mcp_client.call_tool("servers/supplier-intelligence", "get_supplier_status", {"scenario_id": "SCEN-01"})
        self.assertEqual(res4["result"]["delay_status"], "NORMAL")

        # 5. Active decisions
        res5 = self.mcp_client.call_tool("servers/replenishment", "get_active_decisions", {})
        self.assertIn("total_decisions", res5["result"])

    def test_llm_service_intent_and_mcp_routing(self):
        """Verifies natural language queries route to correct MCP tools."""
        # Query 1: Stockout risk
        resp1 = self.llm_service.process_query("Which products are currently at high stockout risk?")
        self.assertTrue(any("Replenishment" in t for t in resp1.tools_used))
        self.assertGreater(len(resp1.tool_traces), 0)
        self.assertTrue(len(resp1.model_name) > 0)

        # Query 2: Replenishment rationale
        resp2 = self.llm_service.process_query("Why is FOODS_1_004 being recommended for replenishment?")
        self.assertTrue(any("Forecasting" in t for t in resp2.tools_used))
        self.assertTrue(any("Replenishment" in t for t in resp2.tools_used))

        # Query 3: Forecast
        resp3 = self.llm_service.process_query("What is the 30-day demand forecast for FOODS category?")
        self.assertTrue(any("Forecasting" in t for t in resp3.tools_used))

        # Query 4: Supplier delays
        resp4 = self.llm_service.process_query("Are there any supplier delivery delays reported?")
        self.assertTrue(any("Supplier Intelligence" in t for t in resp4.tools_used))

        # Query 5: Supervisory decisions
        resp5 = self.llm_service.process_query("What decisions are pending supervisory approval today?")
        self.assertTrue(any("Replenishment" in t for t in resp5.tools_used))

    def test_chat_service_history_and_clear(self):
        """Verifies session history tracking and reset functionality."""
        cs = ChatService()
        initial_len = len(cs.get_history())
        self.assertEqual(initial_len, 1)

        resp = cs.send_message("Which products are at risk?")
        self.assertEqual(len(cs.get_history()), initial_len + 2)
        self.assertEqual(cs.get_history()[-2]["role"], "user")
        self.assertEqual(cs.get_history()[-1]["role"], "assistant")

        cs.clear_history()
        self.assertEqual(len(cs.get_history()), 1)

    def test_chat_service_streaming(self):
        """Verifies asynchronous token streaming into active chat message."""
        import time
        cs = ChatService()
        cs.start_streaming_query("What is the forecast for FOODS?")
        self.assertTrue(cs.is_streaming())
        history = cs.get_history()
        self.assertEqual(len(history), 3)
        self.assertTrue(history[-1].get("is_streaming"))
        # Wait for background worker to complete
        for _ in range(120):
            if not cs.is_streaming():
                break
            time.sleep(0.1)
        final_history = cs.get_history()
        self.assertFalse(cs.is_streaming())
        self.assertFalse(final_history[-1].get("is_streaming"))
        self.assertGreater(len(final_history[-1]["text"]), 0)


    def test_layout_rendering_both_themes(self):
        """Verifies every page view renders under both dark and light themes."""
        for theme in ["dark", "light"]:
            sidebar = render_sidebar("dashboard", theme)
            self.assertIsNotNone(sidebar)

            dash_view = render_dashboard_view(theme)
            self.assertIsNotNone(dash_view)

            inv_view = render_inventory_view(theme)
            self.assertIsNotNone(inv_view)

            dec_view = render_decisions_view(theme)
            self.assertIsNotNone(dec_view)

            copilot_view = render_copilot_view(theme)
            self.assertIsNotNone(copilot_view)

            srv_view = render_services_view(theme)
            self.assertIsNotNone(srv_view)

            for tab in ["forecasting", "m5", "architecture", "hitl"]:
                eval_view = render_evaluation_view(theme, tab)
                self.assertIsNotNone(eval_view)

    def test_sidebar_nav_links(self):
        """Verifies nav links are rendered and active class is applied."""
        links = render_sidebar_nav_links("copilot")
        self.assertEqual(len(links), 6)
        # Check active class is applied to copilot
        copilot_link = [l for l in links if l.id["page"] == "copilot"][0]
        self.assertIn("active", copilot_link.className)
        # Check dashboard link is not active
        dash_link = [l for l in links if l.id["page"] == "dashboard"][0]
        self.assertNotIn("active", dash_link.className)


if __name__ == "__main__":
    unittest.main()

