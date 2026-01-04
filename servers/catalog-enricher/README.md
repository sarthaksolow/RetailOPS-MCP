# Catalog Enricher MCP Server

This MCP server enriches product catalog data by cleaning product names, categorizing items, filling missing fields, and finding alternatives using LLM reasoning.

## Features

- **LangGraph Workflow**: Multi-node reasoning graph for product enrichment
- **Product Name Cleaning**: Normalizes and cleans product names
- **LLM Categorization**: Uses OpenRouter to categorize products intelligently
- **Attribute Extraction**: Extracts brand, description, and attributes
- **Missing Field Detection**: Identifies and fills missing required fields
- **Alternative Products**: Finds alternative products for stockout scenarios
- **AI Narratives**: OpenRouter-powered explanations

## Architecture

The server uses a LangGraph workflow with the following nodes:

1. **load_input**: Loads and parses input product data
2. **clean_name**: Cleans and normalizes product name
3. **categorize**: Categorizes product using LLM reasoning
4. **extract_attributes**: Extracts brand, description, and attributes
5. **find_missing**: Identifies missing required fields
6. **enrich**: Fills in missing fields
7. **find_alternatives**: Finds alternative products
8. **narrative**: Generates AI-powered explanation

## Installation

1. Install dependencies:

```bash
pip install -e .
# or using uv
uv sync
```

2. Set up OpenRouter API key:

```bash
export OPENROUTER_API_KEY=your_key_here
```

Or create a `.env` file:

```
OPENROUTER_API_KEY=your_key_here
```

## Usage

### Run the Server

```bash
python server.py
```

Or on Windows:

```bash
run_server.bat
```

### MCP Tool: `enrichProduct`

**Input Parameters:**
- `product_name` (str): Name of the product to enrich
- `product_data` (dict, optional): Existing product data with any fields

**Output:**
- `product_name`: Cleaned product name
- `category`: Product category
- `brand`: Product brand
- `description`: Product description
- `attributes`: Extracted attributes (size, weight, etc.)
- `missing_fields`: List of fields that were missing
- `alternatives`: List of alternative products (for stockout scenarios)
- `narrative`: AI-generated explanation
- `reasoning`: List of reasoning steps

## Example Use Cases

### Example 1: Basic Product Enrichment

```json
{
  "product_name": "Ariel 2kg Pack",
  "product_data": {}
}
```

**Output:** Enriched product with category, brand, description, and attributes.

### Example 2: Stockout Alternative Finding

```json
{
  "product_name": "Ariel 2kg Detergent Pack",
  "product_data": {
    "category": "groceries"
  }
}
```

**Output:** Enriched product plus alternatives like "Surf Excel 2kg" and "Tide 2kg".

### Example 3: Missing Fields Filling

```json
{
  "product_name": "Samsung TV 55 inch",
  "product_data": {
    "price": 45000
  }
}
```

**Output:** Fills missing category, brand, description automatically.

## Data Files

- `data/product_catalog.json`: Product catalog for finding alternatives
- `data/category_mappings.json`: Category mapping rules

## Integration with Other Servers

This server is designed to work with:
- **Forecasting Server**: Can use enriched category for forecasting
- **Replenishment Server**: Can use alternatives for stockout handling
- **Pricing Strategy Server**: Can use enriched attributes for pricing

## Technical Details

- **Framework**: FastMCP for MCP server implementation
- **Reasoning**: LangGraph for multi-step enrichment workflow
- **AI**: OpenRouter API (Llama 3.1 8B) for categorization and descriptions
- **Communication**: STDIO protocol for MCP

