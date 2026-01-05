"""
Example Usage Scripts for RetailOps MCP Client
"""
import asyncio
import sys
from pathlib import Path

# Add client to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import RetailOpsClient


async def example_1_single_category():
    """Example 1: Full workflow for a single category"""
    print("\n" + "="*70)
    print("📝 EXAMPLE 1: Full Workflow for Single Category")
    print("="*70)
    
    client = RetailOpsClient()
    result = await client.run_full_workflow("tv", days_ahead=30)
    
    print("\n📊 Results Summary:")
    print(f"  Category: {result['category']}")
    print(f"  Status: {result['status']}")
    print(f"\n  📈 Forecast: {result['forecast']['final']} units")
    print(f"     Event: {result['forecast']['event']}")
    print(f"\n  📦 Replenishment: {result['replenishment']['reorder_qty']} units")
    print(f"     Timing: {result['replenishment']['timing']}")
    print(f"     Risk: {result['replenishment']['stockout_risk']}")
    print(f"\n  💰 Pricing: ₹{result['pricing']['recommended_price']}")
    print(f"     Change: {result['pricing']['change_pct']}%")
    print(f"     Type: {result['pricing']['type']}")


async def example_2_batch_processing():
    """Example 2: Batch processing multiple categories"""
    print("\n" + "="*70)
    print("📝 EXAMPLE 2: Batch Processing Multiple Categories")
    print("="*70)
    
    categories = ["electronics", "kitchen_appliances", "fashion"]
    client = RetailOpsClient()
    
    results = await client.run_batch_workflow(categories)
    
    print("\n📊 Batch Results:")
    print("-"*70)
    
    for result in results:
        print(f"\n{result['category'].upper()}:")
        print(f"  Forecast: {result['forecast']['final']} units")
        print(f"  Reorder: {result['replenishment']['reorder_qty']} units ({result['replenishment']['timing']})")
        print(f"  Price: ₹{result['pricing']['recommended_price']} ({result['pricing']['change_pct']}%)")


async def example_3_forecast_only():
    """Example 3: Just forecasting (no replenishment/pricing)"""
    print("\n" + "="*70)
    print("📝 EXAMPLE 3: Forecast Only")
    print("="*70)
    
    client = RetailOpsClient()
    forecast = await client.run_forecast_only("smartphones", days_ahead=30)
    
    print(f"\n📈 Forecast for Smartphones:")
    print(f"  Base Forecast: {forecast.get('base_forecast')}")
    print(f"  Final Forecast: {forecast.get('final_forecast')}")
    print(f"  Seasonal Multiplier: {forecast.get('seasonal_multiplier')}")
    print(f"  Event: {forecast.get('event')}")
    print(f"\n  Narrative: {forecast.get('narrative')}")


async def example_4_error_handling():
    """Example 4: Handling invalid categories"""
    print("\n" + "="*70)
    print("📝 EXAMPLE 4: Error Handling")
    print("="*70)
    
    client = RetailOpsClient()
    
    # Try invalid category
    result = await client.run_full_workflow("invalid_category")
    
    print(f"\n⚠️ Result Status: {result['status']}")
    if result.get('errors'):
        print(f"  Errors: {result['errors']}")


async def example_5_decision_insights():
    """Example 5: Extract actionable insights"""
    print("\n" + "="*70)
    print("📝 EXAMPLE 5: Actionable Decision Insights")
    print("="*70)
    
    client = RetailOpsClient()
    result = await client.run_full_workflow("electronics", days_ahead=30)
    
    print(f"\n🎯 ACTIONABLE INSIGHTS for {result['category'].upper()}:")
    print("-"*70)
    
    # Forecast insights
    forecast = result['forecast']
    print(f"\n📈 DEMAND FORECAST:")
    print(f"   Expected Sales: {forecast['final']} units (next 30 days)")
    if forecast['event'] != 'None':
        print(f"   ⚡ Upcoming Event: {forecast['event']} (multiplier: {forecast['seasonal_multiplier']}x)")
    print(f"   AI Analysis: {forecast['narrative'][:100]}...")
    
    # Replenishment insights
    replenish = result['replenishment']
    print(f"\n📦 INVENTORY ACTION:")
    print(f"   Action Required: {replenish['timing'].upper()}")
    print(f"   Order Quantity: {replenish['reorder_qty']} units")
    print(f"   Stockout Risk: {replenish['stockout_risk'].upper()}")
    print(f"   AI Analysis: {replenish['narrative'][:100]}...")
    
    # Pricing insights
    pricing = result['pricing']
    price_direction = "↑ INCREASE" if pricing['change_pct'] > 0 else "↓ DECREASE" if pricing['change_pct'] < 0 else "→ MAINTAIN"
    print(f"\n💰 PRICING STRATEGY:")
    print(f"   Current Price: ₹{pricing['current_price']}")
    print(f"   Recommended: ₹{pricing['recommended_price']} ({price_direction})")
    print(f"   Strategy: {pricing['type'].upper()}")
    print(f"   AI Analysis: {pricing['narrative'][:100]}...")
    
    # Overall recommendation
    print(f"\n✅ RECOMMENDED ACTIONS:")
    actions = []
    
    if replenish['timing'] == 'immediate':
        actions.append(f"1. URGENT: Order {replenish['reorder_qty']} units immediately")
    elif replenish['timing'] == 'soon':
        actions.append(f"1. Order {replenish['reorder_qty']} units within this week")
    
    if abs(pricing['change_pct']) > 3:
        actions.append(f"2. Adjust price to ₹{pricing['recommended_price']} ({pricing['type']} strategy)")
    
    if forecast['event'] != 'None':
        actions.append(f"3. Prepare for {forecast['event']} - expect {forecast['seasonal_multiplier']}x demand")
    
    for action in actions:
        print(f"   {action}")


async def example_6_catalog_enrichment():
    """Example 6: Catalog enrichment and finding alternatives"""
    print("\n" + "="*70)
    print("📝 EXAMPLE 6: Catalog Enrichment")
    print("="*70)
    
    client = RetailOpsClient()
    
    result = await client.enrich_product("Ariel 2kg Detergent Pack")
    
    print("\n📋 Enrichment Results:")
    print(f"  Product: {result.get('product_name')}")
    print(f"  Category: {result.get('category')}")
    print(f"  Brand: {result.get('brand')}")
    if result.get('alternatives'):
        print(f"\n  🔄 Alternatives: {len(result.get('alternatives', []))} found")
        for alt in result.get('alternatives', [])[:3]:
            print(f"     - {alt.get('name')} ({alt.get('brand')})")


async def run_all_examples():
    """Run all examples"""
    await example_1_single_category()
    await asyncio.sleep(1)
    
    await example_2_batch_processing()
    await asyncio.sleep(1)
    
    await example_3_forecast_only()
    await asyncio.sleep(1)
    
    await example_4_error_handling()
    await asyncio.sleep(1)
    
    await example_5_decision_insights()
    await asyncio.sleep(1)
    
    await example_6_catalog_enrichment()
    
    print("\n" + "="*70)
    print("✅ All examples completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="RetailOps Client Examples")
    parser.add_argument("--example", type=int, choices=[1,2,3,4,5,6], help="Run specific example (1-6)")
    parser.add_argument("--all", action="store_true", help="Run all examples")
    
    args = parser.parse_args()
    
    if args.all:
        asyncio.run(run_all_examples())
    elif args.example == 1:
        asyncio.run(example_1_single_category())
    elif args.example == 2:
        asyncio.run(example_2_batch_processing())
    elif args.example == 3:
        asyncio.run(example_3_forecast_only())
    elif args.example == 4:
        asyncio.run(example_4_error_handling())
    elif args.example == 5:
        asyncio.run(example_5_decision_insights())
    elif args.example == 6:
        asyncio.run(example_6_catalog_enrichment())
    else:
        # Default: run example 1
        asyncio.run(example_1_single_category())
