"""
Test script for Pricing Strategy MCP Server
"""
import asyncio
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession


async def main():
    # Define the MCP server config properly
    config = StdioServerParameters(
        command="python",
        args=["server.py"]
    )

    async with stdio_client(config) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("Connected to Pricing Strategy MCP Server.")
            print("=" * 60)

            # Test Case 1: Excess Inventory - Clearance Pricing
            print("\n📊 Test Case 1: Excess Inventory Scenario")
            print("-" * 60)
            
            response_1 = await session.call_tool(
                "getPricingStrategy",
                {
                    "input": {
                        "category": "electronics",
                        "current_price": 25000.0,
                        "forecasted_demand": 100,
                        "inventory_level": 300,  # High inventory
                        "target_profit_pct": 20
                    }
                }
            )

            print("Pricing Recommendation:")
            print(response_1)

            # Test Case 2: Low Inventory - Premium Pricing
            print("\n📊 Test Case 2: Low Inventory Scenario")
            print("-" * 60)
            
            response_2 = await session.call_tool(
                "getPricingStrategy",
                {
                    "input": {
                        "category": "fashion",
                        "current_price": 1500.0,
                        "forecasted_demand": 200,
                        "inventory_level": 80,  # Low inventory
                        "target_profit_pct": 30
                    }
                }
            )

            print("Pricing Recommendation:")
            print(response_2)

            # Test Case 3: Above Competitor Price - Competitive Pricing
            print("\n📊 Test Case 3: Competitive Adjustment Scenario")
            print("-" * 60)
            
            response_3 = await session.call_tool(
                "getPricingStrategy",
                {
                    "input": {
                        "category": "groceries",
                        "current_price": 150.0,
                        "forecasted_demand": 500,
                        "inventory_level": 600,  # Balanced inventory
                        "target_profit_pct": 15
                    }
                }
            )

            print("Pricing Recommendation:")
            print(response_3)

            # Test Case 4: Balanced - Maintain Pricing
            print("\n📊 Test Case 4: Balanced Scenario")
            print("-" * 60)
            
            response_4 = await session.call_tool(
                "getPricingStrategy",
                {
                    "input": {
                        "category": "home_appliances",
                        "current_price": 8000.0,
                        "forecasted_demand": 150,
                        "inventory_level": 150,  # Balanced 1:1 ratio
                        "target_profit_pct": 25
                    }
                }
            )

            print("Pricing Recommendation:")h
            print(response_4)
            
            print("\n" + "=" * 60)
            print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())