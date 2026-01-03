"""
Test script for Pricing Strategy MCP Server
"""
import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession


async def test_pricing_strategy():
    """Test the pricing strategy server"""
    server_path = Path(__file__).parent / "server.py"
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
        env={}
    )
    
    print("🚀 Testing Pricing Strategy MCP Server")
    print("=" * 60)
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test Case 1: Competitive pricing adjustment
            print("\n📊 Test Case 1: Competitive Pricing Adjustment")
            print("-" * 60)
            test_input_1 = {
                "category": "electronics",
                "current_price": 9000,
                "forecasted_demand": 150,
                "inventory_level": 200,
                "target_profit_pct": 0
            }
            
            response_1 = await session.call_tool(
                "getPricingStrategy",
                test_input_1
            )
            
            if hasattr(response_1, 'content') and response_1.content:
                for content in response_1.content:
                    if hasattr(content, 'text'):
                        result_1 = json.loads(content.text)
                        print(f"Category: {result_1.get('category')}")
                        print(f"Current Price: ₹{result_1.get('current_price')}")
                        print(f"Recommended Price: ₹{result_1.get('recommended_price')}")
                        print(f"Price Change: {result_1.get('price_change_pct')}%")
                        print(f"Recommendation Type: {result_1.get('recommendation_type')}")
                        print(f"Expected Profit Change: {result_1.get('expected_profit_change')}%")
                        print(f"\nNarrative: {result_1.get('narrative')}")
            
            # Test Case 2: Profit optimization
            print("\n📊 Test Case 2: Profit Optimization")
            print("-" * 60)
            test_input_2 = {
                "category": "tv",
                "current_price": 28000,
                "forecasted_demand": 50,
                "inventory_level": 60,
                "target_profit_pct": 5.0
            }
            
            response_2 = await session.call_tool(
                "getPricingStrategy",
                test_input_2
            )
            
            if hasattr(response_2, 'content') and response_2.content:
                for content in response_2.content:
                    if hasattr(content, 'text'):
                        result_2 = json.loads(content.text)
                        print(f"Category: {result_2.get('category')}")
                        print(f"Current Price: ₹{result_2.get('current_price')}")
                        print(f"Recommended Price: ₹{result_2.get('recommended_price')}")
                        print(f"Price Change: {result_2.get('price_change_pct')}%")
                        print(f"Recommendation Type: {result_2.get('recommendation_type')}")
                        print(f"Expected Profit Change: {result_2.get('expected_profit_change')}%")
                        print(f"\nNarrative: {result_2.get('narrative')}")
            
            # Test Case 3: Inventory clearance
            print("\n📊 Test Case 3: Inventory Clearance")
            print("-" * 60)
            test_input_3 = {
                "category": "fashion",
                "current_price": 1500,
                "forecasted_demand": 100,
                "inventory_level": 300,
                "target_profit_pct": 0
            }
            
            response_3 = await session.call_tool(
                "getPricingStrategy",
                test_input_3
            )
            
            if hasattr(response_3, 'content') and response_3.content:
                for content in response_3.content:
                    if hasattr(content, 'text'):
                        result_3 = json.loads(content.text)
                        print(f"Category: {result_3.get('category')}")
                        print(f"Current Price: ₹{result_3.get('current_price')}")
                        print(f"Recommended Price: ₹{result_3.get('recommended_price')}")
                        print(f"Price Change: {result_3.get('price_change_pct')}%")
                        print(f"Recommendation Type: {result_3.get('recommendation_type')}")
                        print(f"Expected Profit Change: {result_3.get('expected_profit_change')}%")
                        print(f"\nNarrative: {result_3.get('narrative')}")
            
            print("\n" + "=" * 60)
            print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_pricing_strategy())

