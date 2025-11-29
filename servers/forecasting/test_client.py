import asyncio
from mcp.client.stdio import stdio_client
from mcp.types import ServerConfig

async def main():
    # Define the MCP server config properly
    config = ServerConfig(
        command="python",
        args=["server.py"]
    )

    async with stdio_client(config) as client:
        print("Connected to Forecasting MCP Server.")

        response = await client.call_tool(
            "getForecast",
            {"category": "tv"}
        )

        print("Forecast Response:")
        print(response)

asyncio.run(main())
