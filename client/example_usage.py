"""
Example usage of the LangGraph forecasting client
"""
import asyncio
from client import forecast_category, forecast_multiple_categories


async def example_single_forecast():
    """Example: Forecast a single category"""
    print("\n" + "="*60)
    print("Example 1: Single Category Forecast")
    print("="*60)
    
    result = await forecast_category("tv", days_ahead=30)
    return result


async def example_multiple_forecasts():
    """Example: Forecast multiple categories"""
    print("\n" + "="*60)
    print("Example 2: Multiple Category Forecasts")
    print("="*60)
    
    categories = ["tv", "laptop", "phone"]
    await forecast_multiple_categories(categories, days_ahead=30)


async def example_custom_workflow():
    """Example: Custom workflow with error handling"""
    print("\n" + "="*60)
    print("Example 3: Custom Workflow with Error Handling")
    print("="*60)
    
    from client import create_forecast_graph
    
    graph = create_forecast_graph()
    
    # Try a valid category
    print("\n--- Valid Category ---")
    result1 = await graph.ainvoke({
        "category": "tv",
        "days_ahead": 30,
        "forecast_result": {},
        "error": None,
        "session": None
    })
    
    # Try an invalid category (to see error handling)
    print("\n--- Invalid Category ---")
    result2 = await graph.ainvoke({
        "category": "nonexistent_category",
        "days_ahead": 30,
        "forecast_result": {},
        "error": None,
        "session": None
    })


async def main():
    """Run all examples"""
    print("🚀 LangGraph Forecasting Client - Examples")
    print("="*60)
    
    # Run examples
    await example_single_forecast()
    await example_multiple_forecasts()
    await example_custom_workflow()
    
    print("\n✅ All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())

