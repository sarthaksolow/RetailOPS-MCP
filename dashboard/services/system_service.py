import os
from pathlib import Path
from typing import List
from dashboard.domain import ServiceStatus


class SystemService:
    def __init__(self):
        self._services_def = [
            {
                "name": "Catalog Enricher",
                "role": "Product classification & metadata enrichment",
                "transport": "stdio (FastMCP JSON-RPC)",
                "entrypoint": "servers/catalog-enricher/server.py",
                "tools": ["enrich_catalog_item", "get_category_attributes"],
                "latency_ms": 9.8,
            },
            {
                "name": "Forecasting",
                "role": "Time-series demand prediction (30d SMA / Holt-Winters)",
                "transport": "stdio (FastMCP JSON-RPC)",
                "entrypoint": "servers/forecasting/server.py",
                "tools": ["get_forecast", "get_seasonal_multiplier"],
                "latency_ms": 7.4,
            },
            {
                "name": "Replenishment",
                "role": "Inventory reasoning & order policy calculation",
                "transport": "stdio (FastMCP JSON-RPC)",
                "entrypoint": "servers/replenishment/server.py",
                "tools": ["calculate_replenishment", "evaluate_runway"],
                "latency_ms": 9.9,
            },
            {
                "name": "Pricing Strategy",
                "role": "Elasticity & margin-aware dynamic pricing",
                "transport": "stdio (FastMCP JSON-RPC)",
                "entrypoint": "servers/pricing-strategy/server.py",
                "tools": ["calculate_pricing", "evaluate_margin"],
                "latency_ms": 10.2,
            },
            {
                "name": "Supplier Intelligence",
                "role": "Supplier reliability scoring & lead-time analysis",
                "transport": "stdio (FastMCP JSON-RPC)",
                "entrypoint": "servers/supplier-intelligence/server.py",
                "tools": ["analyze_supplier_reliability", "recommend_supplier"],
                "latency_ms": 8.5,
            },
        ]

    def get_service_statuses(self) -> List[ServiceStatus]:
        statuses: List[ServiceStatus] = []
        repo_root = Path(__file__).resolve().parent.parent.parent
        for s in self._services_def:
            full_path = repo_root / s["entrypoint"]
            is_present = full_path.exists()
            status_label = "ACTIVE" if is_present else "CONFIGURED"
            statuses.append(
                ServiceStatus(
                    name=s["name"],
                    role=s["role"],
                    transport=s["transport"],
                    status=status_label,
                    tool_count=len(s["tools"]),
                    tools=s["tools"],
                    latency_ms=s["latency_ms"],
                )
            )
        return statuses
