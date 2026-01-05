"""
RetailOps MCP Client - Main Module
Simple imports for easy usage
"""
from .orchestrator import (
    RetailOpsClient,
    forecast_category,
    full_retail_analysis,
    batch_analysis,
    server_manager
)

__all__ = [
    'RetailOpsClient',
    'forecast_category',
    'full_retail_analysis',
    'batch_analysis',
    'server_manager'
]

# Convenience function for catalog enrichment
async def enrich_product(product_name: str, product_data: dict = None):
    """Enrich a product using catalog enricher server"""
    from .orchestrator import server_manager
    return await server_manager.call_catalog_enricher(product_name, product_data)
