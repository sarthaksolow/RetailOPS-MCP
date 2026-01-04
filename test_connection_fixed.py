"""
Fixed test script that properly handles server environment
"""
import asyncio
import sys
import os
from pathlib import Path

# Add client to path
client_path = Path(__file__).parent / "client"
sys.path.insert(0, str(client_path))


async def test_with_proper_server():
    """Test with proper server path handling"""
    print("🧪 Testing Client-Server Connection (Fixed)")
    print("=" * 60)
    
    # First, let's check if server dependencies are available
    server_path = Path(__file__).parent / "servers" / "forecasting"
    print(f"\n📂 Server location: {server_path}")
    
    # Check if server file exists
    server_file = server_path / "server.py"
    if not server_file.exists():
        print(f"❌ Server file not found at: {server_file}")
        return False
    
    print(f"✅ Server file found: {server_file}")
    
    # Check for .env file
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        print(f"✅ Environment file found: {env_file}")
        # Load it
        from dotenv import load_dotenv
        load_dotenv(env_file)
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            print(f"✅ OpenRouter API key loaded (starts with: {api_key[:10]}...)")
        else:
            print("⚠️  OpenRouter API key not found in .env")
    else:
        print(f"⚠️  No .env file found at: {env_file}")
    
    # Now try to run the forecast
    try:
        print("\n📡 Attempting to connect to MCP server...")
        print("📊 Requesting forecast for 'tv' category...\n")
        
        # Import after path is set
        from client import forecast_category
        
        result = await forecast_category("tv", days_ahead=30)
        
        if result.get("error"):
            print(f"\n❌ Test Failed: {result['error']}")
            print("\n💡 Possible solutions:")
            print("   1. Make sure server dependencies are installed:")
            print("      cd servers/forecasting && uv sync")
            print("   2. Make sure client dependencies are installed:")
            print("      cd client && uv sync")
            print("   3. Check that .env file has OPENROUTER_API_KEY set")
            return False
        else:
            print("\n✅ Test Passed! Client-Server connection is working.")
            return True
            
    except Exception as e:
        print(f"\n❌ Test Failed with exception: {e}")
        print("\n💡 Troubleshooting steps:")
        print("   1. Install server dependencies:")
        print("      cd D:\\walmart_mcp\\servers\\forecasting")
        print("      uv sync")
        print("   2. Install client dependencies:")
        print("      cd D:\\walmart_mcp\\client")
        print("      uv sync")
        print("   3. Test server independently:")
        print("      cd D:\\walmart_mcp\\servers\\forecasting")
        print("      uv run python server.py")
        import traceback
        traceback.print_exc()
        return False


async def main():
    success = await test_with_proper_server()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 Everything is working! Your MCP setup is ready.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠️  Setup incomplete. Follow the steps above to fix.")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
