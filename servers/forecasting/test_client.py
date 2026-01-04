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
            
            print("Connected to Forecasting MCP Server.")

            response = await session.call_tool(
                "getForecast",
                {"category": "tv"}
            )

            print("Forecast Response:")
            print(response)

asyncio.run(main())
