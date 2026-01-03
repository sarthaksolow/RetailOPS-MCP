# RetailOps MCP - Usage Guide

This guide will help you set up and use the RetailOps MCP system, including all servers (forecasting, replenishment, pricing-strategy) and the client.

## Prerequisites

- **Python 3.11+** (Python 3.12+ recommended)
- **pip** or **uv** package manager
- **OpenRouter API Key** (free tier available at [openrouter.ai](https://openrouter.ai))

## Quick Start

### 1. Install Dependencies

#### Option A: Using pip

```bash
# Install client dependencies
cd client
pip install -r requirements.txt

# Install server dependencies (for each server)
cd ../servers/forecasting
pip install -e .

cd ../replenishment
pip install fastmcp langgraph openai python-dotenv

cd ../pricing-strategy
pip install -e .
```

#### Option B: Using uv (Recommended)

```bash
# Install uv if you don't have it
pip install uv

# Install client dependencies
cd client
uv sync

# Install server dependencies
cd ../servers/forecasting
uv sync

cd ../replenishment
uv sync

cd ../pricing-strategy
uv sync
```

### 2. Set Up Environment Variables

Create a `.env` file in the **root directory** of the project:

```bash
# In the root directory (RetailOPS-MCP/)
touch .env
```

Add your OpenRouter API key:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

**Note:** You can get a free API key from [openrouter.ai](https://openrouter.ai). The servers use the free Llama 3.1 8B model.

### 3. Verify Installation

Test that Python can import the required packages:

```bash
python -c "import fastmcp, langgraph, openai; print('✅ Dependencies installed')"
```

## Running Servers

### Forecasting Server

The forecasting server generates sales forecasts for product categories.

**Run the server:**
```bash
cd servers/forecasting
python server.py
```

Or on Windows:
```bash
cd servers\forecasting
run_server.bat
```

**Test the server:**
```bash
cd servers/forecasting
python test_client.py
```

### Replenishment Server

The replenishment server recommends inventory restocking decisions.

**Run the server:**
```bash
cd servers/replenishment
python server.py
```

**Test the server:**
```bash
cd servers/replenishment
python test_replenishment_graph.py
```

### Pricing Strategy Server

The pricing strategy server recommends pricing adjustments based on market conditions.

**Run the server:**
```bash
cd servers/pricing-strategy
python server.py
```

Or on Windows:
```bash
cd servers\pricing-strategy
run_server.bat
```

**Test the server:**
```bash
cd servers/pricing-strategy
python test_pricing.py
```

## Using the Client

The client connects to MCP servers via STDIO and orchestrates workflows using LangGraph.

### Basic Usage

**Run the example client:**
```bash
# From the root directory
python client/__init__.py
```

Or:
```bash
python -m client
```

**Run example usage scripts:**
```bash
python client/example_usage.py
```

### Programmatic Usage

#### Example 1: Forecasting

```python
import asyncio
from client import forecast_category, forecast_multiple_categories

async def main():
    # Forecast a single category
    result = await forecast_category("tv", days_ahead=30)
    print(result)
    
    # Forecast multiple categories
    await forecast_multiple_categories(["tv", "laptop", "phone"], days_ahead=30)

asyncio.run(main())
```

#### Example 2: Direct MCP Server Calls

You can also call MCP servers directly using the MCP client:

```python
import asyncio
import json
import sys
from pathlib import Path
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession

async def call_pricing_server():
    server_path = Path("servers/pricing-strategy/server.py")
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
        env={"OPENROUTER_API_KEY": "your_key_here"}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Call the pricing strategy tool
            response = await session.call_tool(
                "getPricingStrategy",
                {
                    "category": "electronics",
                    "current_price": 9000,
                    "forecasted_demand": 150,
                    "inventory_level": 200,
                    "target_profit_pct": 0
                }
            )
            
            # Parse response
            if hasattr(response, 'content') and response.content:
                for content in response.content:
                    if hasattr(content, 'text'):
                        result = json.loads(content.text)
                        print(json.dumps(result, indent=2))

asyncio.run(call_pricing_server())
```

## Complete Workflow Example

Here's how to use multiple servers together:

```python
import asyncio
import json
import sys
from pathlib import Path
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession

async def complete_workflow():
    """Example: Forecast → Replenish → Price"""
    
    # Step 1: Get forecast
    forecast_server = Path("servers/forecasting/server.py")
    forecast_params = StdioServerParameters(
        command=sys.executable,
        args=[str(forecast_server)],
        env={"OPENROUTER_API_KEY": "your_key"}
    )
    
    async with stdio_client(forecast_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            forecast_resp = await session.call_tool("getForecast", {
                "category": "electronics",
                "days_ahead": 30
            })
            
            # Parse forecast
            forecast_data = json.loads(forecast_resp.content[0].text)
            print(f"Forecast: {forecast_data['final_forecast']}")
    
    # Step 2: Get replenishment recommendation
    replenish_server = Path("servers/replenishment/server.py")
    replenish_params = StdioServerParameters(
        command=sys.executable,
        args=[str(replenish_server)],
        env={"OPENROUTER_API_KEY": "your_key"}
    )
    
    async with stdio_client(replenish_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            replenish_resp = await session.call_tool("getReplenishmentDecision", {
                "category": "electronics",
                "forecast": {
                    "forecasted_demand": forecast_data['final_forecast'],
                    "avg_daily_demand": forecast_data['final_forecast'] / 30,
                    "demand_volatility": "medium",
                    "event": {"name": forecast_data.get('event'), "days_to_event": 10}
                },
                "inventory": {
                    "current_stock": 200,
                    "in_transit_stock": 50
                },
                "supplier": {
                    "lead_time_days": 10,
                    "minimum_order_quantity": 50
                }
            })
            
            replenish_data = json.loads(replenish_resp.content[0].text)
            print(f"Replenish: {replenish_data['reorder_qty']} units")
    
    # Step 3: Get pricing strategy
    pricing_server = Path("servers/pricing-strategy/server.py")
    pricing_params = StdioServerParameters(
        command=sys.executable,
        args=[str(pricing_server)],
        env={"OPENROUTER_API_KEY": "your_key"}
    )
    
    async with stdio_client(pricing_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            pricing_resp = await session.call_tool("getPricingStrategy", {
                "category": "electronics",
                "current_price": 9000,
                "forecasted_demand": forecast_data['final_forecast'],
                "inventory_level": 200,
                "target_profit_pct": 5.0
            })
            
            pricing_data = json.loads(pricing_resp.content[0].text)
            print(f"Recommended Price: ₹{pricing_data['recommended_price']}")
            print(f"Expected Profit Change: {pricing_data['expected_profit_change']}%")

asyncio.run(complete_workflow())
```

## Troubleshooting

### Issue: "OPENROUTER_API_KEY not set"

**Solution:** Make sure you've created a `.env` file in the root directory with your API key:
```env
OPENROUTER_API_KEY=your_key_here
```

### Issue: "Module not found" errors

**Solution:** Install dependencies for each component:
```bash
# Client
cd client && pip install -r requirements.txt

# Each server
cd servers/forecasting && pip install -e .
cd servers/replenishment && pip install fastmcp langgraph openai python-dotenv
cd servers/pricing-strategy && pip install -e .
```

### Issue: Server won't start

**Solution:** 
1. Check that Python 3.10+ is installed: `python --version`
2. Verify dependencies are installed
3. Check that data files exist in `servers/*/data/` directories
4. Ensure `.env` file exists with `OPENROUTER_API_KEY`

### Issue: Client can't connect to server

**Solution:**
1. Make sure the server is running (or the client will start it automatically)
2. Check that server paths are correct in client code
3. Verify Python executable path: `which python` or `where python`

## Project Structure

```
RetailOPS-MCP/
├── .env                    # Environment variables (create this)
├── USAGE.md                # This file
├── client/                 # LangGraph client for orchestrating servers
│   ├── __init__.py
│   ├── example_usage.py
│   └── requirements.txt
└── servers/                # MCP servers
    ├── forecasting/        # Sales forecasting server
    ├── replenishment/       # Inventory replenishment server
    └── pricing-strategy/   # Dynamic pricing server
```

## Next Steps

1. **Explore the servers:** Run each server's test file to see them in action
2. **Modify data:** Edit JSON/CSV files in `servers/*/data/` to customize behavior
3. **Create workflows:** Build custom LangGraph workflows combining multiple servers
4. **Integrate with Claude Desktop:** Configure MCP servers in Claude Desktop settings

## Additional Resources

- **Forecasting Server:** See `servers/forecasting/README.md`
- **Replenishment Server:** See `servers/replenishment/server.py` (inline docs)
- **Pricing Strategy Server:** See `servers/pricing-strategy/README.md`
- **Client Documentation:** See `client/README.md`

## Support

For issues or questions:
1. Check server logs (printed to stderr)
2. Review test files for usage examples
3. Verify environment variables are set correctly

