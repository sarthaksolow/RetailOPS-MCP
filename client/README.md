# LangGraph Client for Forecasting MCP Server

This client uses LangGraph to orchestrate calls to the forecasting MCP server, providing a structured workflow for generating sales forecasts.

## Features

- **LangGraph Workflow**: Structured state management and workflow orchestration
- **MCP Integration**: Connects to the forecasting MCP server via STDIO
- **Error Handling**: Robust error handling and session management
- **Multiple Categories**: Support for forecasting multiple categories in sequence
- **Formatted Output**: Clean, readable forecast results

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. (Optional) Set up OpenRouter API key for narrative generation:

```bash
export OPENROUTER_API_KEY=your_key_here
```

Or create a `.env` file in the project root:

```
OPENROUTER_API_KEY=your_key_here
```

## Usage

### Basic Usage

Run the client with default examples:

```bash
python -m client
```

Or from the project root:

```bash
python client/__init__.py
```

### Programmatic Usage

```python
import asyncio
from client import forecast_category, forecast_multiple_categories

# Forecast a single category
async def example():
    result = await forecast_category("tv", days_ahead=30)
    print(result)

# Forecast multiple categories
async def example_multiple():
    await forecast_multiple_categories(["tv", "laptop", "phone"], days_ahead=30)

asyncio.run(example())
```

### Run Examples

```bash
python client/example_usage.py
```

### Custom Workflow

You can also create custom workflows by modifying the graph:

```python
from client import create_forecast_graph

graph = create_forecast_graph()

# Run with custom state
result = await graph.ainvoke({
    "category": "tv",
    "days_ahead": 30,
    "forecast_result": {},
    "error": None,
    "session": None
})
```

## How It Works

1. **State Management**: Uses LangGraph's `StateGraph` to manage workflow state
2. **MCP Connection**: Creates an MCP session using `stdio_client` to connect to the server
3. **Tool Calling**: Calls the `getForecast` tool on the MCP server
4. **Result Processing**: Formats and displays the forecast results

## Workflow Structure

```
Entry Point
    ↓
[forecast] → Call MCP getForecast tool
    ↓
[process] → Format and display results
    ↓
END
```

## Error Handling

The client handles:
- Connection errors to the MCP server
- Tool call failures
- JSON parsing errors
- Server-side errors

All errors are captured in the state and displayed appropriately.

## Requirements

- Python 3.10+
- Access to the forecasting MCP server (in `../servers/forecasting/`)
- Required Python packages (see `requirements.txt`)

## Project Structure

```
client/
├── __init__.py          # Main client module
├── example_usage.py     # Example usage scripts
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

