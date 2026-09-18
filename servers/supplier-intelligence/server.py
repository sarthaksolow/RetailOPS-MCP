"""
Supplier Intelligence MCP Server for RetailOps (Task 08).
Provides deterministic supplier intelligence analysis without external LLM/API calls.

Tool Name: getSupplierIntelligence
Input:
  category (str): Product retail category (e.g. "electronics", "fashion", "groceries")
  reorder_qty (int, optional): Recommended units to reorder (default: 100)

Output:
  supplier_id (str): Identifier of recommended supplier
  supplier_name (str): Full legal or trading name of supplier
  category (str): Associated product category
  reliability_score (float): Historical delivery reliability (0.0 to 1.0)
  lead_time_days (int): Expected delivery lead time in days
  risk_category (str): Evaluated risk tier ("low", "medium", "high")
  on_time_delivery_rate (float): Delivery punctuality rate (0.0 to 1.0)
  quality_rating (float): Verified quality inspection score (0.0 to 5.0)
  cost_index (float): Benchmark pricing multiplier relative to market median
  recommended_supplier (str): Recommended supplier vendor name
  narrative (str): Human-readable risk and fulfillment assessment narrative
"""
import sys
import os
from typing import Dict, Any, Optional
from pathlib import Path
from mcp.server.fastmcp import FastMCP

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

def log(msg: str):
    print(f"[SUPPLIER-INTELLIGENCE] {msg}", file=sys.stderr, flush=True)

mcp = FastMCP("supplier-intelligence-server")

# Deterministic Supplier Knowledge Base
DETERMINISTIC_SUPPLIER_CATALOG: Dict[str, Dict[str, Any]] = {
    "electronics": {
        "supplier_id": "SUP-ELEC-001",
        "supplier_name": "Apex Micro-Logistics Ltd.",
        "reliability_score": 0.94,
        "lead_time_days": 8,
        "risk_category": "low",
        "on_time_delivery_rate": 0.96,
        "quality_rating": 4.8,
        "cost_index": 1.02,
        "tier": "tier_1"
    },
    "tv": {
        "supplier_id": "SUP-DISP-004",
        "supplier_name": "VisionDisplay Global Components",
        "reliability_score": 0.91,
        "lead_time_days": 10,
        "risk_category": "low",
        "on_time_delivery_rate": 0.93,
        "quality_rating": 4.6,
        "cost_index": 1.00,
        "tier": "tier_1"
    },
    "laptop": {
        "supplier_id": "SUP-COMP-002",
        "supplier_name": "SiliconRoute Assemblies",
        "reliability_score": 0.88,
        "lead_time_days": 12,
        "risk_category": "medium",
        "on_time_delivery_rate": 0.89,
        "quality_rating": 4.5,
        "cost_index": 0.98,
        "tier": "tier_2"
    },
    "phone": {
        "supplier_id": "SUP-MOBI-009",
        "supplier_name": "NexGen Telecom Solutions",
        "reliability_score": 0.93,
        "lead_time_days": 7,
        "risk_category": "low",
        "on_time_delivery_rate": 0.95,
        "quality_rating": 4.7,
        "cost_index": 1.05,
        "tier": "tier_1"
    },
    "kitchen_appliances": {
        "supplier_id": "SUP-APPL-005",
        "supplier_name": "HomeCraft Electro-Mechanical Ltd.",
        "reliability_score": 0.82,
        "lead_time_days": 14,
        "risk_category": "medium",
        "on_time_delivery_rate": 0.84,
        "quality_rating": 4.1,
        "cost_index": 0.95,
        "tier": "tier_2"
    },
    "fashion": {
        "supplier_id": "SUP-TEXT-003",
        "supplier_name": "PrimeWeave International",
        "reliability_score": 0.79,
        "lead_time_days": 18,
        "risk_category": "medium",
        "on_time_delivery_rate": 0.81,
        "quality_rating": 4.0,
        "cost_index": 0.91,
        "tier": "tier_2"
    },
    "groceries": {
        "supplier_id": "SUP-AGRI-007",
        "supplier_name": "FarmDirect Logistics Co-Op",
        "reliability_score": 0.74,
        "lead_time_days": 4,
        "risk_category": "high",
        "on_time_delivery_rate": 0.76,
        "quality_rating": 3.9,
        "cost_index": 0.88,
        "tier": "tier_3"
    },
    "general": {
        "supplier_id": "SUP-GEN-999",
        "supplier_name": "Standard Merchandising Distributors",
        "reliability_score": 0.80,
        "lead_time_days": 15,
        "risk_category": "medium",
        "on_time_delivery_rate": 0.82,
        "quality_rating": 4.0,
        "cost_index": 1.00,
        "tier": "tier_2"
    }
}


def compute_supplier_intelligence(
    category: str,
    reorder_qty: Optional[int] = 100
) -> Dict[str, Any]:
    """
    Deterministic domain logic to assess supplier reliability, risk, and lead time.
    """
    cat_key = (category or "").lower().strip()
    sup = DETERMINISTIC_SUPPLIER_CATALOG.get(cat_key, DETERMINISTIC_SUPPLIER_CATALOG["general"]).copy()

    safe_qty = int(reorder_qty) if reorder_qty is not None else 100

    # Adjust lead time dynamically for large order volumes
    lead_time = sup["lead_time_days"]
    if safe_qty > 500:
        lead_time += 3
    elif safe_qty > 200:
        lead_time += 1

    rel_score = sup["reliability_score"]
    risk = sup["risk_category"]
    sup_name = sup["supplier_name"]

    narrative = (
        f"Selected primary vendor '{sup_name}' (ID: {sup['supplier_id']}) with "
        f"{rel_score*100:.0f}% reliability and {risk} supply risk tier. "
        f"Estimated fulfillment lead time is {lead_time} days for order size of {safe_qty} units."
    )

    return {
        "supplier_id": sup["supplier_id"],
        "supplier_name": sup_name,
        "category": cat_key or "general",
        "reliability_score": rel_score,
        "lead_time_days": lead_time,
        "risk_category": risk,
        "on_time_delivery_rate": sup["on_time_delivery_rate"],
        "quality_rating": sup["quality_rating"],
        "cost_index": sup["cost_index"],
        "recommended_supplier": sup_name,
        "narrative": narrative
    }


@mcp.tool()
async def getSupplierIntelligence(
    category: str,
    reorder_qty: Optional[int] = 100
) -> Dict[str, Any]:
    """
    MCP tool exposing deterministic supplier intelligence assessment.
    """
    log(f">>> getSupplierIntelligence called for category: '{category}', reorder_qty: {reorder_qty}")

    # Validation
    if not category or not isinstance(category, str):
        return {
            "error": "Invalid input: category must be a non-empty string."
        }

    try:
        result = compute_supplier_intelligence(category, reorder_qty)
        log(f">>> Supplier Intelligence computed: {result['supplier_name']} ({result['risk_category']} risk)")
        return result
    except Exception as e:
        log(f"❌ Error computing supplier intelligence: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    log(">>> Starting Supplier Intelligence MCP Server (STDIO)")
    mcp.run()
