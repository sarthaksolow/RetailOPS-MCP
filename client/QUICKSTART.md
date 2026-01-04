# 🚀 Quick Start Guide - RetailOps Client

Get up and running with the RetailOps MCP Client in 5 minutes!

## Step 1: Install Dependencies

```bash
cd client
pip install -r requirements.txt
```

## Step 2: Quick Test

```bash
python test_client.py
```

You should see:
```
🧪 QUICK TEST: RetailOps Client
======================================================================

1️⃣ Initializing client...
   ✅ Client initialized

2️⃣ Testing full workflow for 'tv' category...
   ✅ Workflow completed successfully!

   📊 Quick Summary:
      Forecast: 526.35 units
      Reorder: 250 units
      Price: ₹26600
```

## Step 3: Try the CLI

### Single Category Analysis
```bash
python cli.py analyze tv
```

### Batch Processing
```bash
python cli.py batch electronics fashion groceries
```

### Forecast Only
```bash
python cli.py forecast laptop --days 60
```

## Step 4: Use in Your Code

### Simple Usage
```python
import asyncio
from client import full_retail_analysis

async def main():
    result = await full_retail_analysis("tv")
    print(f"Forecast: {result['forecast']['final']} units")

asyncio.run(main())
```

### Advanced Usage
```python
import asyncio
from client import RetailOpsClient

async def main():
    client = RetailOpsClient()
    
    # Single category
    result = await client.run_full_workflow("electronics")
    
    # Batch processing
    categories = ["tv", "laptop", "phone"]
    results = await client.run_batch_workflow(categories)
    
    # Forecast only
    forecast = await client.run_forecast_only("fashion")

asyncio.run(main())
```

## Step 5: Run Examples

```bash
# Run all examples
python examples.py --all

# Or run specific examples
python examples.py --example 1  # Single category
python examples.py --example 2  # Batch processing
python examples.py --example 3  # Forecast only
python examples.py --example 4  # Error handling
python examples.py --example 5  # Decision insights
```

## 🎯 Common Use Cases

### Daily Analysis Script
```python
import asyncio
from client import batch_analysis

async def daily_report():
    categories = ["electronics", "fashion", "groceries"]
    results = await batch_analysis(categories)
    
    for result in results:
        print(f"{result['category']}: {result['forecast']['final']} units")

asyncio.run(daily_report())
```

### Export to JSON
```bash
python cli.py json tv --days 30 > tv_analysis.json
```

### Integration with Cron
```bash
# Add to crontab for daily 9 AM analysis
0 9 * * * cd /path/to/walmart_mcp/client && python daily_analysis.py
```

## 📚 Next Steps

- Read the [full client README](README.md)
- Check out [example scripts](examples.py)
- Explore the [orchestrator code](orchestrator.py)
- Review [server documentation](../servers/)

## 🐛 Troubleshooting

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Server connection failed"
Make sure `.env` file exists in project root with:
```
OPENROUTER_API_KEY=your_key_here
```

### "No data for category"
Check that the category exists in `servers/forecasting/data/sales_history.csv`

## 💡 Tips

1. **Start small**: Test with one category first
2. **Check logs**: Look at stderr output for detailed info
3. **Use CLI**: Great for quick testing and demos
4. **Batch wisely**: Don't overwhelm the system with too many parallel requests
5. **Handle errors**: Always check `result['status']` and `result['errors']`

## ✅ You're Ready!

The client is now fully configured and ready to use. Happy analyzing! 🎉
