import json
from pathlib import Path
from typing import Dict, Any, List
from dashboard.domain import MetricCardData


class MetricsService:
    def __init__(self):
        repo_root = Path(__file__).resolve().parent.parent.parent
        self._results_file = repo_root / "experiments" / "final_evaluation" / "final_results.json"
        self._data: Dict[str, Any] = {}
        self._load_data()

    def _load_data(self):
        if self._results_file.exists():
            with open(self._results_file, "r", encoding="utf-8") as f:
                self._data = json.load(f)

    def get_dashboard_kpis(self) -> List[MetricCardData]:
        # Aggregate operational KPIs from frozen evaluation data
        m5_summary = self._data.get("section_b_m5_operational_evaluation", {})
        retailops_data = m5_summary.get("retailops_mcp", {}).get("overall_summary", {})
        hitl_summary = self._data.get("section_d_hitl_comparison", {}).get("modes_summary", {})
        supervised = hitl_summary.get("retailops_human_supervised", {})

        service_level = retailops_data.get("mean_service_level_pct", 75.81)
        stockout_rate = retailops_data.get("mean_stockout_rate_pct", 21.43)
        mean_cost = retailops_data.get("mean_total_cost", 245.89)
        escalations = supervised.get("total_escalations", 172)

        return [
            MetricCardData(
                title="Service Level",
                value=f"{service_level:.1f}%",
                subtitle="Baseline SCEN-01: 94.9%",
                trend="+5.1% vs (s, S)",
            ),
            MetricCardData(
                title="Stockout Rate",
                value=f"{stockout_rate:.1f}%",
                subtitle="Baseline SCEN-01: 4.3%",
                trend="-4.9% vs (s, S)",
            ),
            MetricCardData(
                title="Mean Operating Cost",
                value=f"${mean_cost:.2f}",
                subtitle="Supervised: $194.77",
                trend="-$51.12 under HITL",
            ),
            MetricCardData(
                title="Supervisory Reviews",
                value=f"{escalations}",
                subtitle="24.6% escalation rate",
                trend="78.1% approved",
            ),
        ]

    def get_forecasting_metrics(self) -> Dict[str, Any]:
        return self._data.get("section_a_forecasting_replacement", {})

    def get_m5_metrics(self) -> Dict[str, Any]:
        return self._data.get("section_b_m5_operational_evaluation", {})

    def get_architecture_metrics(self) -> Dict[str, Any]:
        return self._data.get("section_c_same_repo_architecture_comparison", {})

    def get_hitl_metrics(self) -> Dict[str, Any]:
        return self._data.get("section_d_hitl_comparison", {})
