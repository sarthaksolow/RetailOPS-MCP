"""
RetailOps CLI - Command Line Interface
Easy command-line access to retail operations workflows
"""
import asyncio
import sys
import json
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import RetailOpsClient


def print_banner():
    """Print CLI banner"""
    print("\n" + "="*70)
    print("🛍️  RetailOps MCP Client - CLI")
    print("="*70 + "\n")


def print_result(result: dict):
    """Pretty print workflow result"""
    print(f"\n{'='*70}")
    print(f"📊 RESULTS FOR: {result['category'].upper()}")
    print(f"{'='*70}")
    
    # Status
    status_emoji = "✅" if result['status'] == 'completed' else "⚠️"
    print(f"\nStatus: {status_emoji} {result['status']}")
    
    if result.get('errors'):
        print(f"\n❌ Errors:")
        for error in result['errors']:
            print(f"   - {error}")
        return
    
    # Forecast
    forecast = result.get('forecast', {})
    print(f"\n📈 FORECAST:")
    print(f"   Base Forecast: {forecast.get('base')} units")
    print(f"   Final Forecast: {forecast.get('final')} units")
    print(f"   Seasonal Multiplier: {forecast.get('seasonal_multiplier')}x")
    print(f"   Upcoming Event: {forecast.get('event')}")
    
    # Replenishment
    replenish = result.get('replenishment', {})
    print(f"\n📦 REPLENISHMENT:")
    print(f"   Reorder Quantity: {replenish.get('reorder_qty')} units")
    print(f"   Timing: {replenish.get('timing').upper()}")
    print(f"   Stockout Risk: {replenish.get('stockout_risk').upper()}")
    
    # Pricing
    pricing = result.get('pricing', {})
    change = pricing.get('change_pct', 0)
    arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
    print(f"\n💰 PRICING:")
    print(f"   Current Price: ₹{pricing.get('current_price')}")
    print(f"   Recommended: ₹{pricing.get('recommended_price')} ({arrow} {change}%)")
    print(f"   Strategy: {pricing.get('type').upper()}")
    
    print(f"\n{'='*70}\n")


def print_batch_results(results: List[dict]):
    """Pretty print batch results"""
    print(f"\n{'='*70}")
    print(f"📊 BATCH RESULTS ({len(results)} categories)")
    print(f"{'='*70}\n")
    
    for i, result in enumerate(results, 1):
        cat = result['category']
        forecast = result.get('forecast', {}).get('final', 'N/A')
        reorder = result.get('replenishment', {}).get('reorder_qty', 'N/A')
        price = result.get('pricing', {}).get('recommended_price', 'N/A')
        
        print(f"{i}. {cat.upper():<20} | Forecast: {forecast:>8} | Reorder: {reorder:>6} | Price: ₹{price}")
    
    print(f"\n{'='*70}\n")


async def cmd_analyze(category: str, days: int = 30):
    """Run full workflow for a category"""
    print_banner()
    print(f"🎯 Analyzing category: {category}")
    print(f"📅 Forecast period: {days} days")
    
    client = RetailOpsClient()
    result = await client.run_full_workflow(category, days_ahead=days)
    
    print_result(result)


async def cmd_batch(categories: List[str], days: int = 30):
    """Run batch analysis for multiple categories"""
    print_banner()
    print(f"🎯 Batch analyzing {len(categories)} categories")
    print(f"📅 Forecast period: {days} days")
    
    client = RetailOpsClient()
    results = await client.run_batch_workflow(categories, days_ahead=days)
    
    print_batch_results(results)


async def cmd_forecast(category: str, days: int = 30):
    """Run forecast only"""
    print_banner()
    print(f"🎯 Forecasting: {category}")
    print(f"📅 Period: {days} days")
    
    client = RetailOpsClient()
    forecast = await client.run_forecast_only(category, days_ahead=days)
    
    if 'error' in forecast:
        print(f"\n❌ Error: {forecast['error']}\n")
        return
    
    print(f"\n{'='*70}")
    print(f"📈 FORECAST RESULTS")
    print(f"{'='*70}")
    print(f"\nCategory: {forecast.get('category')}")
    print(f"Base Forecast: {forecast.get('base_forecast')} units")
    print(f"Final Forecast: {forecast.get('final_forecast')} units")
    print(f"Seasonal Multiplier: {forecast.get('seasonal_multiplier')}x")
    print(f"Event: {forecast.get('event')}")
    print(f"\nNarrative:")
    print(f"{forecast.get('narrative')}")
    print(f"\n{'='*70}\n")


async def cmd_json(category: str, days: int = 30):
    """Output results as JSON"""
    client = RetailOpsClient()
    result = await client.run_full_workflow(category, days_ahead=days)
    print(json.dumps(result, indent=2))


def print_help():
    """Print help message"""
    print("""
🛍️  RetailOps CLI - Help

USAGE:
    python cli.py <command> [options]

COMMANDS:
    analyze <category> [--days N]
        Run full workflow (forecast + replenishment + pricing) for a category
        Example: python cli.py analyze tv --days 30

    batch <cat1> <cat2> ... [--days N]
        Run full workflow for multiple categories in parallel
        Example: python cli.py batch tv laptop phone --days 30

    forecast <category> [--days N]
        Run forecast only (no replenishment or pricing)
        Example: python cli.py forecast electronics --days 30

    json <category> [--days N]
        Output results as JSON (useful for scripts)
        Example: python cli.py json tv --days 30 > output.json

    help
        Show this help message

OPTIONS:
    --days N            Forecast horizon in days (default: 30)

SUPPORTED CATEGORIES:
    - electronics
    - tv
    - laptop
    - phone
    - smartphones
    - kitchen_appliances
    - fashion
    - groceries

EXAMPLES:
    # Analyze TV category
    python cli.py analyze tv

    # Batch process multiple categories
    python cli.py batch electronics fashion groceries

    # Get 60-day forecast
    python cli.py forecast laptop --days 60

    # Output as JSON for automation
    python cli.py json phone --days 30 > phone_analysis.json

For more information, see: client/README.md
""")


async def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "help":
            print_help()
        
        elif command == "analyze":
            if len(sys.argv) < 3:
                print("❌ Error: Missing category")
                print("Usage: python cli.py analyze <category> [--days N]")
                return
            
            category = sys.argv[2]
            days = 30
            
            if "--days" in sys.argv:
                days_idx = sys.argv.index("--days")
                if days_idx + 1 < len(sys.argv):
                    days = int(sys.argv[days_idx + 1])
            
            await cmd_analyze(category, days)
        
        elif command == "batch":
            if len(sys.argv) < 3:
                print("❌ Error: Missing categories")
                print("Usage: python cli.py batch <cat1> <cat2> ... [--days N]")
                return
            
            # Extract categories (everything before --days)
            args = sys.argv[2:]
            days = 30
            
            if "--days" in args:
                days_idx = args.index("--days")
                days = int(args[days_idx + 1])
                categories = args[:days_idx]
            else:
                categories = args
            
            await cmd_batch(categories, days)
        
        elif command == "forecast":
            if len(sys.argv) < 3:
                print("❌ Error: Missing category")
                print("Usage: python cli.py forecast <category> [--days N]")
                return
            
            category = sys.argv[2]
            days = 30
            
            if "--days" in sys.argv:
                days_idx = sys.argv.index("--days")
                if days_idx + 1 < len(sys.argv):
                    days = int(sys.argv[days_idx + 1])
            
            await cmd_forecast(category, days)
        
        elif command == "json":
            if len(sys.argv) < 3:
                print("❌ Error: Missing category")
                print("Usage: python cli.py json <category> [--days N]")
                return
            
            category = sys.argv[2]
            days = 30
            
            if "--days" in sys.argv:
                days_idx = sys.argv.index("--days")
                if days_idx + 1 < len(sys.argv):
                    days = int(sys.argv[days_idx + 1])
            
            await cmd_json(category, days)
        
        else:
            print(f"❌ Unknown command: {command}")
            print("Run 'python cli.py help' for usage information")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
