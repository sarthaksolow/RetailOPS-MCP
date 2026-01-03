# Pricing Strategy MCP Server

This MCP server provides intelligent pricing strategy recommendations using LangGraph for multi-step reasoning and OpenRouter for AI-generated narratives.

## Features

- **LangGraph Workflow**: Multi-node reasoning graph for pricing decisions
- **Price Elasticity Analysis**: Category-specific elasticity modeling
- **Competitor Analysis**: Market positioning and competitive pricing
- **Inventory Pressure Analysis**: Stock level considerations
- **Profit Optimization**: Target profit margin calculations
- **AI Narratives**: OpenRouter-powered explanations

## Architecture

The server uses a LangGraph workflow with the following nodes:

1. **load_data**: Loads category-specific elasticity and competitor data
2. **competitor_analysis**: Analyzes competitive positioning
3. **elasticity_analysis**: Calculates price elasticity impact
4. **inventory_analysis**: Evaluates inventory pressure
5. **pricing_decision**: Makes pricing recommendation with impact calculations
6. **narrative**: Generates AI-powered explanation

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
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

Or using the batch file (Windows):

```bash
run_server.bat
```

### MCP Tool: `getPricingStrategy`

**Input Parameters:**
- `category` (str): Product category (e.g., "electronics", "tv", "laptop")
- `current_price` (float): Current selling price
- `forecasted_demand` (float): Expected demand from forecasting server
- `inventory_level` (float): Current inventory units
- `target_profit_pct` (float, optional): Target profit percentage

**Output:**
- `category`: Product category
- `current_price`: Current price
- `recommended_price`: Recommended price
- `price_change_pct`: Percentage change
- `recommendation_type`: Type of recommendation (discount, increase, maintain, etc.)
- `expected_demand_change`: Expected demand change percentage
- `expected_revenue_change`: Expected revenue change percentage
- `expected_profit_change`: Expected profit change percentage
- `narrative`: AI-generated explanation
- `explanation_factors`: List of factors considered

## Example Use Cases

### Example 1: Competitive Pricing Adjustment

```json
{
  "category": "electronics",
  "current_price": 9000,
  "forecasted_demand": 150,
  "inventory_level": 200,
  "target_profit_pct": 0
}
```

**Output:** Recommends price reduction if overpriced compared to competitors.

### Example 2: Profit Optimization

```json
{
  "category": "tv",
  "current_price": 28000,
  "forecasted_demand": 50,
  "inventory_level": 60,
  "target_profit_pct": 5.0
}
```

**Output:** Optimizes price to meet profit target while considering elasticity.

### Example 3: Inventory Clearance

```json
{
  "category": "fashion",
  "current_price": 1500,
  "forecasted_demand": 100,
  "inventory_level": 300,
  "target_profit_pct": 0
}
```

**Output:** Recommends discount to clear excess inventory.

## Data Files

- `data/price_elasticity.json`: Category-specific price elasticity coefficients, margins, and discount limits
- `data/competitor_prices.json`: Competitor pricing data for market positioning

## Integration with Other Servers

This server is designed to work with:
- **Forecasting Server**: Uses `forecasted_demand` from forecasting server
- **Replenishment Server**: Can inform replenishment decisions based on pricing strategy

## Technical Details

- **Framework**: FastMCP for MCP server implementation
- **Reasoning**: LangGraph for multi-step decision workflow
- **AI**: OpenRouter API (Llama 3.1 8B) for narrative generation
- **Communication**: STDIO protocol for MCP

## Error Handling

The server handles:
- Missing category data (uses defaults)
- API failures (falls back to template narratives)
- Invalid inputs (returns error messages)
- Edge cases (maintains minimum margins)

