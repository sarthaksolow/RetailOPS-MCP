"""
Test script for Replenishment MCP Server
"""
import asyncio
import json
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession


async def main():
    # Load test data
    with open("mock_replenishment_inputs.json") as f:
        mock_inputs = json.load(f)
    
    # Define the MCP server config properly
    config = StdioServerParameters(
        command="python",
        args=["server.py"]
    )

    async with stdio_client(config) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("Connected to Replenishment MCP Server.")
            print("=" * 60)

            # Test Case 1: Festival too close
            print("\n📊 Test Case 1: Festival Scenario")
            print("-" * 60)
            
            # Get scenario description if it exists
            test_1 = mock_inputs[0]
            if "scenario" in test_1:
                print(f"Scenario: {test_1['scenario']}")
            
            response_1 = await session.call_tool(
                "getReplenishmentDecision",
                {"input": test_1}
            )

            print("\nReplenishment Decision:")
            print(response_1)

            # Test Case 2: Slow sales, overstocked
            print("\n📊 Test Case 2: Overstocked Scenario")
            print("-" * 60)
            
            test_2 = mock_inputs[1]
            if "scenario" in test_2:
                print(f"Scenario: {test_2['scenario']}")
            
            response_2 = await session.call_tool(
                "getReplenishmentDecision",
                {"input": test_2}
            )

            print("\nReplenishment Decision:")
            print(response_2)
            
            print("\n" + "=" * 60)
            print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())