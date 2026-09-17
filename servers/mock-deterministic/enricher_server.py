import sys
import os
from typing import Dict, Any
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Ensure root is importable for baseline algorithms
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from baseline.tightly_coupled import TightlyCoupledRetailOps

def log(msg: str):
    print(f"[MOCK-ENRICHER] {msg}", file=sys.stderr, flush=True)

mcp = FastMCP("mock-enricher-server")
baseline = TightlyCoupledRetailOps()

@mcp.tool()
async def enrichProduct(input: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic catalog enrichment without external LLM calls."""
    product_name = input.get("product_name", "")
    product_data = input.get("product_data", {})
    res = baseline.direct_enrich_product(product_name, product_data)
    return res

if __name__ == "__main__":
    log(">>> Starting Mock Deterministic Catalog Enricher (STDIO)")
    mcp.run()
