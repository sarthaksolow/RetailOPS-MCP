# RetailOps MCP Client

A **LangGraph-based orchestrator** that chains together Forecasting, Replenishment, and Pricing Strategy MCP servers into intelligent retail operations workflows.

## 🎯 What This Does

The client orchestrates three MCP servers in a sequential workflow:

```
📊 FORECASTING → 📦 REPLENISHMENT → 💰 PRICING → 📈 INSIGHTS
```

### Workflow Stages:

1. **Forecasting Node**: Predicts demand based on sales history + seasonal events
2. **Replenishment Node**: Calculates optimal reorder quantities and timing
3. **Pricing Node**: Recommends price adjustments based on inventory and competition

## 🚀 Quick Start

### Installation

```bash
cd client
pip install -r requirements.txt
```

### Basic Usage

```python
import asyncio
from client import RetailOpsClient

async def main():
    client = RetailOpsClient()
    
    # Run full workflow
    result = await client.run_full_workflow("tv", days_ahead=30)
    
    print(f"Forecast: {result['forecast']['final']} units")
    print(f"Reorder: {result['replenishment']['reorder_qty']} units")
    print(f"Price: ₹{result['pricing']['recommended_price']}")

asyncio.run(main())
```

### Quick Test

```bash
python test_client.py
```

### Run Examples

```bash
# Run all examples
python examples.py --all

# Run specific example
python examples.py --example 1
python examples.py --example 2
# etc.
```

## 📚 API Reference

### RetailOpsClient

Main client class for orchestrating retail operations workflows.

#### Methods

##### `run_full_workflow(category: str, days_ahead: int = 30)`

Runs complete workflow: Forecast → Replenishment → Pricing

**Parameters:**
- `category` (str): Product category (e.g., "tv", "electronics", "fashion")
- `days_ahead` (int): Forecast horizon in days (default: 30)

**Returns:**
```python
{
    "category": "tv",
    "timestamp": "2026-01-04T...",
    "status": "completed",
    "forecast": {
        "base": 145.2,
        "final": 526.35,
        "seasonal_multiplier": 1.45,
        "event": "Diwali",
        "narrative": "AI explanation..."
    },
    "replenishment": {
        "reorder_qty": 250,
        "timing": "immediate",
        "stockout_risk": "high",
        "narrative": "AI explanation..."
    },
    "pricing": {
        "current_price": 28000,
        "recommended_price": 26600,
        "change_pct": -5.0,
        "type": "competitive",
        "narrative": "AI explanation..."
    },
    "errors": []
}
```

##### `run_forecast_only(category: str, days_ahead: int = 30)`

Runs only the forecasting server (no replenishment or pricing).

##### `run_batch_workflow(categories: List[str], days_ahead: int = 30)`

Runs full workflow for multiple categories in parallel.

**Example:**
```python
categories = ["tv", "laptop", "phone"]
results = await client.run_batch_workflow(categories)
```

### Convenience Functions

#### `forecast_category(category: str, days_ahead: int = 30)`

Quick function for forecasting only (no client initialization needed).

#### `full_retail_analysis(category: str, days_ahead: int = 30)`

Quick function for full workflow (no client initialization needed).

#### `batch_analysis(categories: List[str], days_ahead: int = 30)`

Quick function for batch processing (no client initialization needed).

## 🏗️ Architecture

### LangGraph Workflow

```python
StateGraph:
  Nodes:
    - forecast: Call forecasting MCP server
    - replenish: Call replenishment MCP server  
    - price: Call pricing MCP server
  
  Flow:
    forecast → replenish → price → END
```

### State Management

The workflow maintains a comprehensive state object that accumulates data from each server:

- **Input**: category, days_ahead
- **Forecasting outputs**: forecast_data, base_forecast, final_forecast, etc.
- **Replenishment outputs**: reorder_qty, timing, stockout_risk, etc.
- **Pricing outputs**: recommended_price, price_change_pct, etc.
- **Metadata**: errors, workflow_status, timestamp

### Error Handling

- Each node can fail independently
- Errors are accumulated in `state["errors"]`
- Workflow stops if a critical node fails
- Partial results are still returned

## 📊 Example Workflows

### Example 1: Single Category Analysis

```python
client = RetailOpsClient()
result = await client.run_full_workflow("tv")

print(f"Forecast: {result['forecast']['final']} units")
print(f"Reorder: {result['replenishment']['reorder_qty']} units")
print(f"Price: ₹{result['pricing']['recommended_price']}")
```

### Example 2: Batch Processing

```python
categories = ["electronics", "kitchen_appliances", "fashion"]
results = await client.run_batch_workflow(categories)

for result in results:
    print(f"{result['category']}: {result['forecast']['final']} units")
```

### Example 3: Forecast Only

```python
client = RetailOpsClient()
forecast = await client.run_forecast_only("smartphones")
print(f"Forecast: {forecast['final_forecast']} units")
```

## 🎨 Features

### ✅ Implemented

- **LangGraph orchestration**: Sequential workflow with state management
- **Parallel batch processing**: Run multiple categories simultaneously
- **Error handling**: Graceful failure with partial results
- **AI-powered narratives**: Natural language explanations from each server
- **Comprehensive logging**: Detailed stderr logs for debugging
- **Type safety**: TypedDict state definitions
- **Flexible API**: Multiple convenience functions

### 🔜 Future Enhancements

- **Conditional routing**: Smart decisions based on intermediate results
- **Retry logic**: Automatic retry for transient failures
- **Caching**: Cache forecast results to reduce API calls
- **Config management**: Externalized inventory levels, prices, etc.
- **Webhooks**: Real-time notifications for critical decisions
- **Data persistence**: Store workflow results in database

## 🧪 Testing

### Test Client Connection

```bash
python test_client.py
```

### Run All Examples

```bash
python examples.py --all
```

### Individual Examples

```bash
# Single category workflow
python examples.py --example 1

# Batch processing
python examples.py --example 2

# Forecast only
python examples.py --example 3

# Error handling
python examples.py --example 4

# Decision insights
python examples.py --example 5
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_key_here
```

### Server Paths

The client automatically finds MCP servers at:
- `../servers/forecasting/server.py`
- `../servers/replenishment/server.py`
- `../servers/pricing-strategy/server.py`

### Default Parameters

Can be customized in `orchestrator.py`:

```python
# Replenishment defaults
current_stock = 200
in_transit = 50
lead_time_days = 10
minimum_order_quantity = 50

# Pricing defaults
default_prices = {
    "electronics": 9000,
    "tv": 28000,
    # etc.
}
```

## 🐛 Troubleshooting

### Issue: "Module not found"

**Solution:**
```bash
cd client
pip install -r requirements.txt
```

### Issue: "Server connection failed"

**Solution:**
1. Verify MCP servers exist in `../servers/` directories
2. Check that Python is in PATH
3. Ensure `.env` file exists with `OPENROUTER_API_KEY`

### Issue: "Workflow status: failed_forecast"

**Solution:**
1. Check that the category exists in sales_history.csv
2. Verify forecasting server has required data files
3. Check stderr logs for detailed error messages

## 📝 Advanced Usage

### Custom Inventory Levels

Modify the `replenishment_node` in `orchestrator.py`:

```python
replenish_data = await server_manager.call_replenishment(
    state["forecast_data"],
    current_stock=500,  # Custom value
    in_transit=100      # Custom value
)
```

### Custom Prices

Modify the `pricing_node` in `orchestrator.py`:

```python
pricing_data = await server_manager.call_pricing(
    state["category"],
    state["final_forecast"],
    inventory_level=300,    # Custom value
    current_price=35000     # Custom value
)
```

### Add Custom Nodes

Extend the workflow with additional processing:

```python
async def custom_node(state: RetailOpsState) -> RetailOpsState:
    # Your custom logic here
    state["custom_data"] = "some value"
    return state

# Add to graph
workflow.add_node("custom", custom_node)
workflow.add_edge("price", "custom")
workflow.add_edge("custom", END)
```

## 🤝 Integration Examples

### Use in Scripts

```python
from client import full_retail_analysis
import asyncio

async def daily_analysis():
    categories = ["tv", "laptop", "phone"]
    
    for category in categories:
        result = await full_retail_analysis(category)
        # Send to dashboard, email, etc.
        send_to_dashboard(result)

asyncio.run(daily_analysis())
```

### Use in Web API

```python
from fastapi import FastAPI
from client import RetailOpsClient

app = FastAPI()
client = RetailOpsClient()

@app.get("/analyze/{category}")
async def analyze(category: str):
    result = await client.run_full_workflow(category)
    return result
```

### Use in Scheduled Jobs

```python
import schedule
import asyncio
from client import batch_analysis

def job():
    categories = ["electronics", "fashion", "groceries"]
    results = asyncio.run(batch_analysis(categories))
    # Process results...

schedule.every().day.at("09:00").do(job)
```

## 📖 Related Documentation

- [Forecasting Server](../servers/forecasting/README.md)
- [Replenishment Server](../servers/replenishment/server.py)
- [Pricing Strategy Server](../servers/pricing-strategy/README.md)
- [Main Project README](../USAGE.md)

## 🎓 Learn More

- **LangGraph**: https://langchain-ai.github.io/langgraph
- **MCP Protocol**: https://modelcontextprotocol.io
- **Async Python**: https://docs.python.org/3/library/asyncio.html

## 📄 License

Part of the RetailOps MCP project.
