import os
import sys
import json
from typing import TypedDict, Dict, Any, List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from langgraph.graph import StateGraph
from openai import OpenAI

# =====================================================
# ENV + STDIO SAFE LOGGING
# =====================================================
load_dotenv()

def log(msg: str):
    print(msg, file=sys.stderr, flush=True)

log(">>> Loading Catalog Enricher MCP Server")

# =====================================================
# OpenRouter Client
# =====================================================
api_key = os.getenv("OPENROUTER_API_KEY")

client = None
if api_key:
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "http://localhost",
            "X-Title": "RetailOPS Catalog Enricher"
        }
    )
    log(">>> OpenRouter configured")
else:
    log("⚠️ OPENROUTER_API_KEY not found – running fallback mode")

# =====================================================
# MCP INIT
# =====================================================
mcp = FastMCP("catalog-enricher-server")

# =====================================================
# LOAD DATA
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Load product catalog and category mappings
try:
    catalog_path = os.path.join(DATA_DIR, "product_catalog.json")
    if os.path.exists(catalog_path):
        with open(catalog_path, "r") as f:
            product_catalog = json.load(f)
        log(f">>> Product catalog loaded: {len(product_catalog)} products")
    else:
        product_catalog = {}
        log(">>> No product catalog found, using empty catalog")
    
    category_mappings_path = os.path.join(DATA_DIR, "category_mappings.json")
    if os.path.exists(category_mappings_path):
        with open(category_mappings_path, "r") as f:
            category_mappings = json.load(f)
        log(f">>> Category mappings loaded: {len(category_mappings)} categories")
    else:
        category_mappings = {}
        log(">>> No category mappings found, using empty mappings")
        
except Exception as e:
    log(f"⚠️ Error loading data files: {e}")
    product_catalog = {}
    category_mappings = {}

# =====================================================
# STATE
# =====================================================
class CatalogEnrichmentState(TypedDict):
    input: Dict[str, Any]
    
    product_name: str
    product_data: Dict[str, Any]
    
    cleaned_name: str
    category: str
    brand: str
    description: str
    attributes: Dict[str, Any]
    
    missing_fields: List[str]
    enriched_fields: Dict[str, Any]
    
    alternatives: List[Dict[str, Any]]
    reasoning: List[str]
    narrative: str

# =====================================================
# GRAPH NODES
# =====================================================
def load_input_node(state: CatalogEnrichmentState):
    """Load and parse input product data"""
    input_data = state["input"]
    state["product_name"] = input_data.get("product_name", "")
    state["product_data"] = input_data.get("product_data", {})
    state["reasoning"] = []
    return state


def clean_name_node(state: CatalogEnrichmentState):
    """Clean and normalize product name"""
    name = state["product_name"]
    
    # Basic cleaning
    cleaned = name.strip()
    cleaned = " ".join(cleaned.split())  # Normalize whitespace
    
    # Remove common prefixes/suffixes
    prefixes = ["New", "Best", "Premium", "Super"]
    for prefix in prefixes:
        if cleaned.startswith(prefix + " "):
            cleaned = cleaned[len(prefix) + 1:]
    
    state["cleaned_name"] = cleaned
    state["reasoning"].append(f"cleaned product name: '{name}' -> '{cleaned}'")
    return state


def categorize_node(state: CatalogEnrichmentState):
    """Categorize product using LLM reasoning"""
    name = state["cleaned_name"]
    existing_data = state["product_data"]
    
    # Check if category already exists
    if "category" in existing_data and existing_data["category"]:
        state["category"] = existing_data["category"]
        state["reasoning"].append(f"using existing category: {state['category']}")
        return state
    
    # Use LLM to categorize
    if client is None:
        # Fallback: simple keyword matching
        name_lower = name.lower()
        if any(word in name_lower for word in ["tv", "television", "screen"]):
            state["category"] = "electronics"
        elif any(word in name_lower for word in ["laptop", "computer", "notebook"]):
            state["category"] = "electronics"
        elif any(word in name_lower for word in ["phone", "smartphone", "mobile"]):
            state["category"] = "electronics"
        elif any(word in name_lower for word in ["detergent", "soap", "shampoo", "pack"]):
            state["category"] = "groceries"
        elif any(word in name_lower for word in ["shirt", "pants", "dress", "fashion"]):
            state["category"] = "fashion"
        else:
            state["category"] = "general"
        state["reasoning"].append(f"fallback categorization: {state['category']}")
        return state
    
    prompt = f"""
Categorize this product into one of these retail categories:
- electronics
- groceries
- fashion
- kitchen_appliances
- home_appliances
- beauty_personal_care
- sports_fitness
- general

Product name: {name}

Respond with ONLY the category name, nothing else.
"""
    
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.1
        )
        category = response.choices[0].message.content.strip().lower()
        # Validate category
        valid_categories = ["electronics", "groceries", "fashion", "kitchen_appliances", 
                          "home_appliances", "beauty_personal_care", "sports_fitness", "general"]
        if category not in valid_categories:
            category = "general"
        state["category"] = category
        state["reasoning"].append(f"LLM categorized as: {category}")
    except Exception as e:
        log(f"Categorization error: {e}")
        state["category"] = "general"
        state["reasoning"].append(f"categorization failed, defaulting to 'general'")
    
    return state


def extract_attributes_node(state: CatalogEnrichmentState):
    """Extract product attributes using LLM"""
    name = state["cleaned_name"]
    existing_data = state["product_data"]
    
    # Extract brand
    if "brand" in existing_data and existing_data["brand"]:
        state["brand"] = existing_data["brand"]
    else:
        # Simple brand extraction (first word often)
        words = name.split()
        if words:
            state["brand"] = words[0].title()
        else:
            state["brand"] = "Unknown"
    
    # Generate description if missing
    if "description" in existing_data and existing_data["description"]:
        state["description"] = existing_data["description"]
    else:
        if client:
            prompt = f"""Generate a brief product description (1-2 sentences) for: {name}
Be concise and professional."""
            try:
                response = client.chat.completions.create(
                    model="meta-llama/llama-3.1-8b-instruct",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=60
                )
                state["description"] = response.choices[0].message.content.strip()
            except:
                state["description"] = f"Product: {name}"
        else:
            state["description"] = f"Product: {name}"
    
    # Extract attributes (size, weight, etc.)
    attributes = existing_data.get("attributes", {})
    
    # Try to extract size/weight from name
    import re
    weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(kg|g|lb|oz)', name, re.IGNORECASE)
    if weight_match and "weight" not in attributes:
        attributes["weight"] = weight_match.group(0)
    
    size_match = re.search(r'(\d+(?:\.\d+)?)\s*(ml|l|oz)', name, re.IGNORECASE)
    if size_match and "size" not in attributes:
        attributes["size"] = size_match.group(0)
    
    state["attributes"] = attributes
    state["reasoning"].append(f"extracted brand: {state['brand']}, attributes: {len(attributes)} fields")
    
    return state


def find_missing_fields_node(state: CatalogEnrichmentState):
    """Identify missing required fields"""
    required_fields = ["category", "brand", "description"]
    missing = []
    
    if not state.get("category"):
        missing.append("category")
    if not state.get("brand"):
        missing.append("brand")
    if not state.get("description"):
        missing.append("description")
    
    state["missing_fields"] = missing
    if missing:
        state["reasoning"].append(f"missing fields: {', '.join(missing)}")
    else:
        state["reasoning"].append("all required fields present")
    
    return state


def enrich_fields_node(state: CatalogEnrichmentState):
    """Fill in missing fields using LLM reasoning"""
    enriched = {}
    
    for field in state["missing_fields"]:
        if field == "category" and not state.get("category"):
            # Already handled in categorize_node
            continue
        elif field == "description" and not state.get("description"):
            # Already handled in extract_attributes_node
            continue
        elif field == "brand" and not state.get("brand"):
            # Already handled in extract_attributes_node
            continue
    
    state["enriched_fields"] = enriched
    return state


def find_alternatives_node(state: CatalogEnrichmentState):
    """Find alternative products (for stockout scenarios)"""
    category = state["category"]
    brand = state.get("brand", "")
    name = state["cleaned_name"]
    
    alternatives = []
    
    # Search in catalog for similar products
    if product_catalog:
        for product_id, product in product_catalog.items():
            if product.get("category") == category:
                # Don't include the same product
                if product.get("name", "").lower() != name.lower():
                    # Check if different brand (good alternative)
                    if product.get("brand", "") != brand:
                        alternatives.append({
                            "name": product.get("name", ""),
                            "brand": product.get("brand", ""),
                            "category": product.get("category", ""),
                            "price": product.get("price", 0),
                            "margin": product.get("margin_pct", 0)
                        })
                        if len(alternatives) >= 3:  # Limit to 3 alternatives
                            break
    
    # If no alternatives found in catalog, use LLM to suggest
    if not alternatives and client:
        prompt = f"""Given this product is out of stock, suggest 2-3 alternative products in the same category.
Product: {name} (Category: {category}, Brand: {brand})

Respond with a JSON array of alternatives, each with: name, brand, reason.
Example: [{{"name": "Surf Excel 2kg", "brand": "Surf Excel", "reason": "Similar detergent, same size"}}]"""
        
        try:
            response = client.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            result = response.choices[0].message.content.strip()
            # Try to parse JSON
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            result = result.strip()
            alternatives = json.loads(result)
        except:
            pass
    
    state["alternatives"] = alternatives[:3]  # Limit to 3
    if alternatives:
        state["reasoning"].append(f"found {len(alternatives)} alternative products")
    else:
        state["reasoning"].append("no alternatives found")
    
    return state


def narrative_node(state: CatalogEnrichmentState):
    """Generate AI narrative for the enrichment"""
    if client is None:
        state["narrative"] = (
            f"Enriched product: {state['cleaned_name']}. "
            f"Category: {state.get('category', 'N/A')}, "
            f"Brand: {state.get('brand', 'N/A')}. "
            f"Found {len(state.get('alternatives', []))} alternatives."
        )
        return state

    prompt = f"""
You are a retail catalog expert. Summarize the product enrichment:

Product: {state['cleaned_name']}
Category: {state.get('category', 'N/A')}
Brand: {state.get('brand', 'N/A')}
Description: {state.get('description', 'N/A')}
Missing fields filled: {', '.join(state.get('missing_fields', []))}
Alternatives found: {len(state.get('alternatives', []))}

Provide a concise summary (2-3 sentences) of the enrichment work done.
"""
    
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        state["narrative"] = response.choices[0].message.content
    except Exception as e:
        log(f"Narrative generation error: {e}")
        state["narrative"] = (
            f"Enriched product: {state['cleaned_name']}. "
            f"Category: {state.get('category', 'N/A')}, "
            f"Brand: {state.get('brand', 'N/A')}."
        )

    return state

# =====================================================
# BUILD GRAPH
# =====================================================
graph = StateGraph(CatalogEnrichmentState)

graph.add_node("load_input", load_input_node)
graph.add_node("clean_name", clean_name_node)
graph.add_node("categorize", categorize_node)
graph.add_node("extract_attributes", extract_attributes_node)
graph.add_node("find_missing", find_missing_fields_node)
graph.add_node("enrich", enrich_fields_node)
graph.add_node("find_alternatives", find_alternatives_node)
graph.add_node("narrative", narrative_node)

graph.set_entry_point("load_input")

graph.add_edge("load_input", "clean_name")
graph.add_edge("clean_name", "categorize")
graph.add_edge("categorize", "extract_attributes")
graph.add_edge("extract_attributes", "find_missing")
graph.add_edge("find_missing", "enrich")
graph.add_edge("enrich", "find_alternatives")
graph.add_edge("find_alternatives", "narrative")

enrichment_graph = graph.compile()

log(">>> LangGraph compiled successfully")

# =====================================================
# MCP TOOL
# =====================================================
@mcp.tool()
async def enrichProduct(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich product catalog data by cleaning, categorizing, and filling missing fields.
    
    Input should contain:
    - product_name: str (name of the product)
    - product_data: dict (optional, existing product data with any fields)
    """
    log(">>> MCP Tool called: enrichProduct")
    
    result = enrichment_graph.invoke({"input": input})
    
    return {
        "product_name": result["cleaned_name"],
        "category": result.get("category", ""),
        "brand": result.get("brand", ""),
        "description": result.get("description", ""),
        "attributes": result.get("attributes", {}),
        "missing_fields": result.get("missing_fields", []),
        "alternatives": result.get("alternatives", []),
        "narrative": result.get("narrative", ""),
        "reasoning": result.get("reasoning", [])
    }

# =====================================================
# RUN MCP SERVER
# =====================================================
if __name__ == "__main__":
    log(">>> Starting Catalog Enricher MCP Server (STDIO)")
    mcp.run()

