import time
from typing import Dict, Any, List, Optional
from dashboard.services.inventory_service import InventoryService
from dashboard.services.decision_service import DecisionService
from dashboard.services.system_service import SystemService
from dashboard.services.metrics_service import MetricsService


class MCPToolClient:
    """
    Standardized client exposing RetailOps capabilities as callable MCP tools.
    Provides structured input/output payloads and execution telemetry.
    """

    def __init__(self):
        self._inventory_service = InventoryService()
        self._decision_service = DecisionService()
        self._system_service = SystemService()
        self._metrics_service = MetricsService()

    def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch tool invocation to appropriate RetailOps capability with telemetry."""
        start_time = time.perf_counter()
        result_payload = {}

        if tool_name == "get_inventory_status":
            item_id = arguments.get("item_id")
            items = self._inventory_service.get_inventory_items()
            if item_id:
                matched = [it for it in items if item_id.lower() in it.item_id.lower() or item_id.lower() in it.series_id.lower()]
                result_payload = {"matched_count": len(matched), "items": [it.__dict__ for it in matched]}
            else:
                high_risk = [it.__dict__ for it in items if it.stockout_risk == "high"]
                result_payload = {"total_items": len(items), "high_risk_items": high_risk, "all_items": [it.__dict__ for it in items]}

        elif tool_name == "get_forecast":
            category = arguments.get("category", "FOODS")
            days = arguments.get("days", 30)
            fc_data = self._metrics_service.get_forecasting_metrics()
            cat_data = fc_data.get("per_category_comparison", {}).get(category.lower(), {})
            result_payload = {
                "category": category,
                "horizon_days": days,
                "baseline_daily_forecast": cat_data.get("baseline_sma", {}).get("daily_forecast", 3.5),
                "baseline_mae": cat_data.get("baseline_sma", {}).get("mae", 5.84),
                "replacement_model": "Holt-Winters Additive",
                "replacement_mae": cat_data.get("holt_winters_replacement", {}).get("mae", 6.91),
            }

        elif tool_name == "calculate_replenishment":
            series_id = arguments.get("series_id", "CA_1_FOODS_1_004")
            item = self._inventory_service.get_item_by_id(series_id)
            if item:
                result_payload = {
                    "series_id": item.series_id,
                    "on_hand": item.on_hand,
                    "in_transit": item.in_transit,
                    "stock_runway_days": item.runway_days,
                    "lead_time_days": item.lead_time_days,
                    "stockout_risk": item.stockout_risk,
                    "recommended_reorder_qty": item.recommended_order,
                    "rationale": f"Effective runway {item.runway_days:.1f}d against lead time {item.lead_time_days}d. Reorder of {item.recommended_order} units maintains safety stock.",
                }
            else:
                result_payload = {"error": f"Series {series_id} not found."}

        elif tool_name == "get_supplier_status":
            scenario_id = arguments.get("scenario_id", "SCEN-01")
            is_delayed = scenario_id in ["SCEN-04", "SCEN-05"]
            result_payload = {
                "supplier_lead_time_days": 21 if is_delayed else 7,
                "supplier_reliability_rate": 0.70 if is_delayed else 0.95,
                "delay_status": "CRITICAL_DELAY" if is_delayed else "NORMAL",
                "active_scenario": scenario_id,
                "notes": "Extended lead times in SCEN-04 and SCEN-05 require proactive buffer ordering.",
            }

        elif tool_name == "get_active_decisions":
            decisions = self._decision_service.get_all_decisions()
            req_review = [d.__dict__ for d in decisions if d.requires_approval]
            result_payload = {
                "total_decisions": len(decisions),
                "requiring_approval_count": len(req_review),
                "decisions_requiring_approval": req_review,
                "all_decisions": [d.__dict__ for d in decisions],
            }

        else:
            result_payload = {"error": f"Tool {tool_name} not recognized."}

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "server": server_name,
            "tool": tool_name,
            "arguments": arguments,
            "result": result_payload,
            "latency_ms": elapsed_ms,
        }
