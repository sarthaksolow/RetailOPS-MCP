"""
RetailOps MCP Client - Main Package
Exposes the main Orchestrator Client and Server Manager.
"""

from .orchestrator import (
    RetailOpsClient,
    RetailOpsState,
    server_manager
)

from .telemetry import ServiceCallTelemetry, ExecutionTelemetry, TelemetryLogger

__all__ = [
    'RetailOpsClient',
    'RetailOpsState',
    'server_manager',
    'enrich_product',
    'forecast_category',
    'full_retail_analysis',
    'batch_analysis',
    'ServiceCallTelemetry',
    'ExecutionTelemetry',
    'TelemetryLogger'
]

# --- Convenience Functions ---

async def enrich_product(product_name: str) -> dict:
    """
    Directly call the catalog enricher without running the full workflow.
    Useful for quick lookups or debugging.
    """
    return await server_manager.call_enrichment(product_name)

async def forecast_category(category: str, days_ahead: int = 30) -> dict:
    """
    Directly call the forecasting server for a category.
    """
    return await server_manager.call_forecasting(category, days_ahead)

async def full_retail_analysis(product_name: str, days_ahead: int = 30) -> dict:
    """
    Run full retail operations workflow for a product or category.
    """
    client = RetailOpsClient()
    return await client.run_full_workflow(product_name, days_ahead)

async def batch_analysis(product_names: list, days_ahead: int = 30) -> list:
    """
    Run batch retail operations workflow for multiple products or categories.
    """
    client = RetailOpsClient()
    return await client.run_batch_workflow(product_names, days_ahead)