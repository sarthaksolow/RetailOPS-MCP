"""
LangGraph client for the Forecasting MCP Server

This client uses LangGraph to orchestrate calls to the forecasting MCP server,
providing a structured workflow for generating sales forecasts.
"""
import asyncio
import json
import os
import sys
from typing import TypedDict
from contextlib import asynccontextmanager
from pathlib import Path

from langgraph.graph import StateGraph, END
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession


class ForecastState(TypedDict):
    """State for the LangGraph workflow"""
    category: str
    days_ahead: int
    forecast_result: dict
    error: str | None
    session: ClientSession | None


@asynccontextmanager
async def mcp_session():
    """Context manager for MCP session with proper cleanup"""
    # Get the path to the server script (go up one level from client/ to root)
    server_path = Path(__file__).parent.parent / "servers" / "forecasting" / "server.py"
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
        env={"OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", "")}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call_forecast_tool(state: ForecastState) -> ForecastState:
    """Call the getForecast tool from the MCP server"""
    try:
        async with mcp_session() as session:
            response = await session.call_tool(
                "getForecast",
                {
                    "category": state["category"],
                    "days_ahead": state.get("days_ahead", 30)
                }
            )
            
            # Parse response
            if hasattr(response, 'content') and response.content:
                for content in response.content:
                    if hasattr(content, 'text'):
                        try:
                            result = json.loads(content.text)
                            state["forecast_result"] = result
                            return state
                        except json.JSONDecodeError:
                            # If not JSON, try to extract text
                            state["forecast_result"] = {"raw_response": content.text}
                            return state
            
            state["error"] = "No valid response from server"
            return state
            
    except Exception as e:
        state["error"] = str(e)
        import traceback
        traceback.print_exc()
        return state


def process_result(state: ForecastState) -> ForecastState:
    """Process and format the forecast result"""
    if state.get("error"):
        print(f"❌ Error: {state['error']}")
        return state
    
    result = state.get("forecast_result", {})
    
    # Check if it's an error response
    if "error" in result:
        print(f"❌ Server Error: {result['error']}")
        return state
    
    # Display formatted results
    print(f"\n{'='*60}")
    print(f"📊 Forecast for: {result.get('category', 'N/A').upper()}")
    print(f"{'='*60}")
    print(f"   Base Forecast:        {result.get('base_forecast', 'N/A')}")
    print(f"   Seasonal Multiplier:  {result.get('seasonal_multiplier', 'N/A')}")
    print(f"   Historical Surge:     {result.get('historical_surge_factor', 'N/A')}")
    print(f"   Final Forecast:       {result.get('final_forecast', 'N/A')}")
    print(f"   Event:                {result.get('event', 'None')}")
    
    if result.get('narrative'):
        print(f"\n💡 Narrative:")
        print(f"   {result['narrative']}")
    
    print(f"{'='*60}\n")
    
    return state


def create_forecast_graph():
    """Create the LangGraph workflow"""
    workflow = StateGraph(ForecastState)
    
    # Add nodes
    workflow.add_node("forecast", call_forecast_tool)
    workflow.add_node("process", process_result)
    
    # Define edges
    workflow.set_entry_point("forecast")
    workflow.add_edge("forecast", "process")
    workflow.add_edge("process", END)
    
    return workflow.compile()


async def forecast_category(category: str, days_ahead: int = 30) -> dict:
    """
    Generate a forecast for a single category
    
    Args:
        category: Product category to forecast
        days_ahead: Number of days to forecast ahead (default: 30)
    
    Returns:
        Dictionary containing the forecast result
    """
    graph = create_forecast_graph()
    
    result = await graph.ainvoke({
        "category": category,
        "days_ahead": days_ahead,
        "forecast_result": {},
        "error": None,
        "session": None
    })
    
    return result


async def forecast_multiple_categories(categories: list[str], days_ahead: int = 30):
    """
    Generate forecasts for multiple categories
    
    Args:
        categories: List of product categories to forecast
        days_ahead: Number of days to forecast ahead (default: 30)
    """
    graph = create_forecast_graph()
    
    for category in categories:
        await graph.ainvoke({
            "category": category,
            "days_ahead": days_ahead,
            "forecast_result": {},
            "error": None,
            "session": None
        })


async def main():
    """Main entry point for the client"""
    print("🚀 Forecasting Client with LangGraph")
    print("=" * 60)
    
    # Example: forecast for multiple categories
    categories = ["tv", "laptop", "phone"]
    
    await forecast_multiple_categories(categories, days_ahead=30)
    
    # Example: single forecast
    print("\n" + "=" * 60)
    print("Single Category Forecast Example")
    print("=" * 60)
    await forecast_category("tv", days_ahead=30)


if __name__ == "__main__":
    asyncio.run(main())

