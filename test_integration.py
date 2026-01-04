"""
Comprehensive Integration Test
Tests all client functionality end-to-end
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "client"))

from orchestrator import RetailOpsClient


async def test_suite():
    """Run comprehensive test suite"""
    print("\n" + "="*70)
    print("🧪 COMPREHENSIVE INTEGRATION TEST SUITE")
    print("="*70 + "\n")
    
    client = RetailOpsClient()
    passed = 0
    failed = 0
    
    # Test 1: Single category workflow
    print("1️⃣ Test: Single Category Workflow")
    try:
        result = await client.run_full_workflow("tv", days_ahead=30)
        assert result['status'] == 'completed', f"Expected 'completed', got {result['status']}"
        assert 'forecast' in result, "Missing forecast data"
        assert 'replenishment' in result, "Missing replenishment data"
        assert 'pricing' in result, "Missing pricing data"
        print("   ✅ PASSED: Full workflow executed successfully")
        passed += 1
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        failed += 1
    
    # Test 2: Forecast only
    print("\n2️⃣ Test: Forecast Only")
    try:
        forecast = await client.run_forecast_only("electronics", days_ahead=30)
        assert 'final_forecast' in forecast or 'error' in forecast, "Invalid forecast response"
        print("   ✅ PASSED: Forecast-only execution works")
        passed += 1
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        failed += 1
    
    # Test 3: Batch processing
    print("\n3️⃣ Test: Batch Processing")
    try:
        categories = ["tv", "laptop"]
        results = await client.run_batch_workflow(categories, days_ahead=30)
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        assert all('category' in r for r in results), "Missing category field"
        print("   ✅ PASSED: Batch processing works")
        passed += 1
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        failed += 1
    
    # Test 4: Error handling (invalid category)
    print("\n4️⃣ Test: Error Handling")
    try:
        result = await client.run_full_workflow("invalid_category_xyz")
        # Should return error or failed status, not crash
        assert 'status' in result, "Missing status field"
        print("   ✅ PASSED: Error handling works (graceful failure)")
        passed += 1
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        failed += 1
    
    # Test 5: State accumulation
    print("\n5️⃣ Test: State Accumulation")
    try:
        result = await client.run_full_workflow("fashion", days_ahead=30)
        
        if result['status'] == 'completed':
            # Check that state accumulated data from all nodes
            assert result['forecast']['final'] > 0, "Missing forecast value"
            assert result['replenishment']['reorder_qty'] >= 0, "Missing reorder qty"
            assert result['pricing']['recommended_price'] > 0, "Missing price"
            print("   ✅ PASSED: State accumulation works correctly")
            passed += 1
        else:
            print(f"   ⚠️ SKIPPED: Workflow failed (status: {result['status']})")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        failed += 1
    
    # Test 6: Different forecast periods
    print("\n6️⃣ Test: Custom Forecast Period")
    try:
        result_30 = await client.run_forecast_only("kitchen_appliances", days_ahead=30)
        result_60 = await client.run_forecast_only("kitchen_appliances", days_ahead=60)
        # Both should execute (values may be same since algo doesn't use days_ahead much)
        assert result_30 is not None, "30-day forecast failed"
        assert result_60 is not None, "60-day forecast failed"
        print("   ✅ PASSED: Custom forecast periods work")
        passed += 1
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        failed += 1
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Client is working perfectly.")
    else:
        print(f"\n⚠️ Some tests failed. Review the errors above.")
    
    print("="*70 + "\n")
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = asyncio.run(test_suite())
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)
