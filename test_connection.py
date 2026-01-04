"""
Simple test script to verify client-server connection
"""
import asyncio
import sys
from pathlib import Path

# Add client to path
client_path = Path(__file__).parent / "client"
sys.path.insert(0, str(client_path))

from client import forecast_category


async def test_connection():
    """Test the client-server connection"""
    print("🧪 Testing Client-Server Connection")
    print("=" * 60)
    
    try:
        print("\n📡 Attempting to connect to MCP server...")
        print("📊 Requesting forecast for 'tv' category...\n")
        
        result = await forecast_category("tv", days_ahead=30)
        
        if result.get("error"):
            print(f"\n❌ Test Failed: {result['error']}")
            return False
        else:
            print("\n✅ Test Passed! Client-Server connection is working.")
            return True
            
    except Exception as e:
        print(f"\n❌ Test Failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    success = await test_connection()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 Everything is working! Your MCP setup is ready.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠️  There were some issues. Check the errors above.")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
