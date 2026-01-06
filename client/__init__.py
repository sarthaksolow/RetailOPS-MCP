"""
RetailOps MCP Client - Main Package
Exposes the main Orchestrator Client and Server Manager.
"""

from .orchestrator import (
    RetailOpsClient,
    RetailOpsState,
    server_manager
)

__all__ = [
    'RetailOpsClient',
    'RetailOpsState',
    'server_manager',
    'enrich_product'
]

# --- Convenience Functions ---

async def enrich_product(product_name: str) -> dict:
    """
    Directly call the catalog enricher without running the full workflow.
    Useful for quick lookups or debugging.
    """
    # Uses the global server_manager instance from orchestrator.py
    return await server_manager.call_enrichment(product_name)