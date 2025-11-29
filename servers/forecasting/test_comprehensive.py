"""
Comprehensive test script for the forecasting MCP server
"""
import sys
import os
import asyncio
from pathlib import Path

print("=" * 60)
print("FORECASTING SERVER COMPREHENSIVE TEST")
print("=" * 60)

# Test 1: Check Python version
print("\n[1] Checking Python version...")
print(f"Python version: {sys.version}")
if sys.version_info < (3, 10):
    print("❌ ERROR: Python 3.10+ required")
    sys.exit(1)
print("✓ Python version OK")

# Test 2: Check required files
print("\n[2] Checking required files...")
required_files = [
    "server.py",
    "data/sales_history.csv",
    "data/events.json",
    "data/surge_profile.json"
]

for file in required_files:
    if os.path.exists(file):
        print(f"✓ Found: {file}")
    else:
        print(f"❌ Missing: {file}")
        sys.exit(1)

# Test 3: Check dependencies
print("\n[3] Checking dependencies...")
try:
    import pandas as pd
    print("✓ pandas installed")
except ImportError:
    print("❌ pandas not installed")
    sys.exit(1)

try:
    from mcp.server.fastmcp import FastMCP
    print("✓ fastmcp installed")
except ImportError:
    print("❌ fastmcp not installed")
    sys.exit(1)

try:
    import openai
    print("✓ openai installed")
except ImportError:
    print("❌ openai not installed")
    sys.exit(1)

# Test 4: Check environment variables
print("\n[4] Checking environment variables...")
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
if api_key:
    print(f"✓ OPENROUTER_API_KEY found: {api_key[:15]}...")
else:
    print("⚠️  WARNING: OPENROUTER_API_KEY not set (narrative generation will fail)")

# Test 5: Load and validate data files
print("\n[5] Validating data files...")

try:
    import json
    import pandas as pd
    
    # Load sales history
    sales_df = pd.read_csv("data/sales_history.csv")
    print(f"✓ sales_history.csv loaded: {len(sales_df)} rows")
    print(f"  Columns: {list(sales_df.columns)}")
    print(f"  Categories: {sales_df['category'].unique().tolist()}")
    
    # Load events
    with open("data/events.json", "r") as f:
        events = json.load(f)
    print(f"✓ events.json loaded: {len(events.get('events', []))} events")
    
    # Load surge profiles
    with open("data/surge_profile.json", "r") as f:
        surge = json.load(f)
    print(f"✓ surge_profile.json loaded: {len(surge)} profiles")
    
except Exception as e:
    print(f"❌ Error loading data: {e}")
    sys.exit(1)

# Test 6: Test MCP server connection
print("\n[6] Testing MCP server connection...")

try:
    from mcp.client.stdio import StdioServerParameters, stdio_client
    
    async def test_server():
        # Use StdioServerParameters instead of ServerConfig
        server_params = StdioServerParameters(
            command=sys.executable,  # Use current Python interpreter
            args=["server.py"],
            env={"OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY", "")}
        )
        
        print("  Connecting to server...")
        async with stdio_client(server_params) as (read, write):
            print("  ✓ Connected to server!")
            
            # Initialize the session
            from mcp.client.session import ClientSession
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # List available tools
                tools_result = await session.list_tools()
                print(f"  ✓ Available tools: {[t.name for t in tools_result.tools]}")
                
                # Test the getForecast tool
                print("\n  Testing getForecast tool with 'tv' category...")
                response = await session.call_tool(
                    "getForecast",
                    {"category": "tv", "days_ahead": 30}
                )
                
                print("  ✓ Tool call successful!")
                print(f"\n  Response:")
                
                # Parse the response - content is a list of CallToolResult content items
                if hasattr(response, 'content') and response.content:
                    for content in response.content:
                        # Check if it's a TextContent
                        if hasattr(content, 'text'):
                            try:
                                import json
                                result = json.loads(content.text)
                                print(f"    Category: {result.get('category')}")
                                print(f"    Base Forecast: {result.get('base_forecast')}")
                                print(f"    Seasonal Multiplier: {result.get('seasonal_multiplier')}")
                                print(f"    Historical Surge: {result.get('historical_surge_factor')}")
                                print(f"    Final Forecast: {result.get('final_forecast')}")
                                print(f"    Event: {result.get('event')}")
                                if 'narrative' in result:
                                    print(f"\n    Narrative:")
                                    print(f"    {result['narrative']}")
                            except json.JSONDecodeError as e:
                                # If it's not JSON, just print the text
                                print(f"    Text response: {content.text}")
                        else:
                            # Handle other content types
                            print(f"    Content type: {type(content)}")
                            print(f"    Content: {content}")
                else:
                    print(f"    Raw response: {response}")
                
                print("\n" + "=" * 60)
                print("✓ ALL TESTS PASSED!")
                print("Your forecasting server is working correctly!")
                print("=" * 60)
                print("\nYou can now use this server with:")
                print("  1. MCP Inspector: fastmcp dev server.py")
                print("  2. Claude Desktop: Add to claude_desktop_config.json")
                print("  3. Your custom client")
                
                return True
    
    # Run the async test
    asyncio.run(test_server())
    
except Exception as e:
    print(f"\n❌ Server test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
