"""
Quick Test Script for RetailOps Client
Tests the orchestrator connection and workflow
"""
import asyncio
import sys
from pathlib import Path

# Add client to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import RetailOpsClient


async def quick_test():
    """Quick test of the client"""
    print("\n" + "="*70)
    print("🧪 QUICK TEST: RetailOps Client")
    print("="*70)
    
    print("\n1️⃣ Initializing client...")
    client = RetailOpsClient()
    print("   ✅ Client initialized")
    
    print("\n2️⃣ Testing full workflow for 'tv' category...")
    result = await client.run_full_workflow("tv", days_ahead=30)
    
    if result['status'] == 'completed':
        print("   ✅ Workflow completed successfully!")
        print(f"\n   📊 Quick Summary:")
        print(f"      Forecast: {result['forecast']['final']} units")
        print(f"      Reorder: {result['replenishment']['reorder_qty']} units")
        print(f"      Price: ₹{result['pricing']['recommended_price']}")
    else:
        print(f"   ⚠️ Workflow status: {result['status']}")
        if result.get('errors'):
            print(f"   Errors: {result['errors']}")
    
    print("\n" + "="*70)
    print("✅ Test completed!")
    print("="*70 + "\n")
    
    return result


if __name__ == "__main__":
    asyncio.run(quick_test())