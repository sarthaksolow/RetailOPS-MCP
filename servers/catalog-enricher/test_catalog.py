"""
Test script for Catalog Enricher MCP Server
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
            
            print("Connected to Catalog Enricher MCP Server.")
            print("=" * 60)

            # Test Case 1: Basic enrichment
            print("\n📊 Test Case 1: Basic Product Enrichment")
            print("-" * 60)
            
            response_1 = await session.call_tool(
                "enrichProduct",
                {
                    "input": {
                        "product_name": "Ariel 2kg Pack",
                        "product_data": {}
                    }
                }
            )

            print("Response 1:")
            print(response_1)

            # Test Case 2: Stockout alternative finding
            print("\n📊 Test Case 2: Finding Alternatives (Stockout Scenario)")
            print("-" * 60)
            
            response_2 = await session.call_tool(
                "enrichProduct",
                {
                    "input": {
                        "product_name": "Ariel 2kg Detergent Pack",
                        "product_data": {
                            "category": "groceries"
                        }
                    }
                }
            )

            print("Response 2:")
            print(response_2)

            # Test Case 3: Missing fields
            print("\n📊 Test Case 3: Filling Missing Fields")
            print("-" * 60)
            
            response_3 = await session.call_tool(
                "enrichProduct",
                {
                    "input": {
                        "product_name": "Samsung TV 55 inch",
                        "product_data": {
                            "price": 45000
                        }
                    }
                }
            )

            print("Response 3:")
            print(response_3)
            
            print("\n" + "=" * 60)
            print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())