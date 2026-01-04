# 🛍️ RetailOps MCP System

**AI-Powered Retail Operations Suite with LangGraph Orchestration**

A complete Model Context Protocol (MCP) system that chains together forecasting, replenishment, and pricing strategy servers into intelligent retail workflows.

---

## 🎯 What This Does

Transform retail operations with AI-powered decision making:

```
📊 FORECAST → 📦 REPLENISHMENT → 💰 PRICING → 📈 ACTIONABLE INSIGHTS
```

**Example Result:**
- **Forecast**: 526 units demand (TV category, next 30 days, Diwali effect)
- **Replenishment**: Order 250 units immediately (high stockout risk)
- **Pricing**: Reduce to ₹26,600 (-5% competitive strategy)

---

## 🚀 Quick Start (5 Minutes)

### 1. Install Dependencies
```bash
# Install client
cd client
pip install -r requirements.txt
```

### 2. Set Environment
Create `.env` in project root:
```env
OPENROUTER_API_KEY=your_key_here
```
Get free API key at [openrouter.ai](https://openrouter.ai)

### 3. Test It
```bash
python test_client.py
```

### 4. Use It
```bash
# CLI
python cli.py analyze tv

# Python
python -c "import asyncio; from client import full_retail_analysis; print(asyncio.run(full_retail_analysis('tv')))"
```

**That's it!** ✅ You're running AI-powered retail analysis.

---

## 📦 System Components

### 🔌 **3 MCP Servers** (STDIO Protocol)

#### 1. Forecasting Server (`servers/forecasting/`)
- Predicts demand using sales history + seasonal events
- Algorithm: Moving average × seasonal multiplier × surge factor
- AI-powered narrative explanations

#### 2. Replenishment Server (`servers/replenishment/`)
- Recommends optimal reorder quantities and timing
- 7-stage LangGraph reasoning workflow
- Safety stock calculation with festival urgency

#### 3. Pricing Strategy Server (`servers/pricing-strategy/`)
- Dynamic pricing based on inventory, demand, competition
- 3-stage LangGraph workflow
- Considers price elasticity and competitor positioning

### 🧠 **LangGraph Client** (`client/`)
- Orchestrates all servers in intelligent workflows
- Sequential execution with state accumulation
- Parallel batch processing for multiple categories
- Multiple interfaces: CLI, Python API, convenience functions

---

## 💻 Usage Examples

### CLI Interface
```bash
# Single category analysis
python cli.py analyze tv

# Batch processing
python cli.py batch electronics fashion groceries

# Forecast only
python cli.py forecast laptop --days 60

# JSON output
python cli.py json phone > analysis.json
```

### Python API
```python
from client import RetailOpsClient
import asyncio

async def main():
    client = RetailOpsClient()
    
    # Full workflow
    result = await client.run_full_workflow("tv")
    print(f"Forecast: {result['forecast']['final']} units")
    print(f"Reorder: {result['replenishment']['reorder_qty']} units")
    print(f"Price: ₹{result['pricing']['recommended_price']}")

asyncio.run(main())
```

### Convenience Functions
```python
from client import full_retail_analysis, batch_analysis
import asyncio

# Quick single analysis
result = asyncio.run(full_retail_analysis("tv"))

# Batch processing
results = asyncio.run(batch_analysis(["tv", "laptop", "phone"]))
```

---

## 📊 Sample Output

```json
{
  "category": "tv",
  "status": "completed",
  "forecast": {
    "base": 145.2,
    "final": 526.35,
    "seasonal_multiplier": 1.45,
    "event": "Diwali",
    "narrative": "Strong demand expected due to upcoming Diwali..."
  },
  "replenishment": {
    "reorder_qty": 250,
    "timing": "immediate",
    "stockout_risk": "high",
    "narrative": "Immediate reorder needed to prevent stockout..."
  },
  "pricing": {
    "current_price": 28000,
    "recommended_price": 26600,
    "change_pct": -5.0,
    "type": "competitive",
    "narrative": "Price reduction recommended to match competitors..."
  }
}
```

---

## 🏗️ Architecture

```
┌─────────────────┐
│   CLI / API     │ ← User interfaces
└────────┬────────┘
         │
    ┌────▼──────────┐
    │  ORCHESTRATOR │ ← LangGraph workflow
    │  (Client)     │
    └────┬──────────┘
         │
    ┌────┼────┬─────────┐
    │    │    │         │
┌───▼┐ ┌─▼──┐ ┌─▼─────┐
│ F  │→│ R  │→│ P     │ ← MCP Servers
│ O  │ │ E  │ │ R     │
│ R  │ │ P  │ │ I     │
│ E  │ │ L  │ │ C     │
│ C  │ │ E  │ │ I     │
│ A  │ │ N  │ │ N     │
│ S  │ │    │ │ G     │
│ T  │ │    │ │       │
└────┘ └────┘ └───────┘
```

**Data Flow:**
1. User requests analysis for category
2. Orchestrator initializes LangGraph workflow
3. Forecast node gets demand prediction
4. Replenishment node calculates reorder needs
5. Pricing node recommends price adjustments
6. Results aggregated and returned

---

## 🎓 Features

### ✅ Implemented
- **LangGraph orchestration** - Smart workflow management
- **3 AI-powered servers** - Forecasting, replenishment, pricing
- **Multiple interfaces** - CLI, Python API, convenience functions
- **Parallel batch processing** - Analyze multiple categories
- **Error handling** - Graceful failures with partial results
- **AI narratives** - Natural language explanations
- **Type safety** - Full type hints
- **Comprehensive testing** - Unit and integration tests
- **Complete documentation** - README, quickstart, examples

### 🔜 Future Enhancements
- Web dashboard UI
- Database persistence
- Result caching
- Advanced ML models
- A/B testing framework
- Real-time webhooks
- Multi-region support

---

## 📚 Documentation

### Quick Start
- **[Quick Start Guide](client/QUICKSTART.md)** - Get running in 5 minutes
- **[Test Client](test_client.py)** - Verify your setup

### Detailed Guides
- **[Client README](client/README.md)** - Complete client documentation
- **[Architecture Diagram](ARCHITECTURE_DIAGRAM.md)** - Visual system overview
- **[Project Analysis](PROJECT_ANALYSIS.md)** - Deep dive into architecture
- **[Usage Guide](USAGE.md)** - Original setup guide

### Examples & Tests
- **[Examples](client/examples.py)** - 5 comprehensive usage examples
- **[Integration Tests](test_integration.py)** - Full test suite
- **[CLI Help](client/cli.py)** - Command-line interface

---

## 🧪 Testing

### Quick Test
```bash
python test_client.py
```

### Comprehensive Test
```bash
python test_integration.py
```

### Run Examples
```bash
cd client
python examples.py --all
```

---

## 📦 Installation

### Prerequisites
- Python 3.11+ (3.12+ recommended)
- pip or uv package manager
- OpenRouter API key (free tier available)

### Client Installation
```bash
cd client
pip install -r requirements.txt
```

### Server Installation (Optional - servers start automatically)
```bash
# Forecasting
cd servers/forecasting
pip install -e .

# Replenishment
cd servers/replenishment
pip install fastmcp langgraph openai python-dotenv

# Pricing
cd servers/pricing-strategy
pip install -e .
```

---

## 🗂️ Project Structure

```
walmart_mcp/
├── client/                    # ⭐ LangGraph orchestrator
│   ├── orchestrator.py       # Main workflow engine
│   ├── cli.py               # Command-line interface
│   ├── examples.py          # Usage examples
│   ├── test_client.py       # Quick test
│   └── README.md            # Client documentation
│
├── servers/                  # MCP servers
│   ├── forecasting/         # Demand prediction
│   ├── replenishment/       # Inventory decisions
│   └── pricing-strategy/    # Dynamic pricing
│
├── test_integration.py      # Integration test suite
├── QUICKSTART.md           # 5-minute guide
├── ARCHITECTURE_DIAGRAM.md # Visual architecture
└── README.md               # This file
```

---

## 🔧 Configuration

### Environment Variables
```env
OPENROUTER_API_KEY=your_openrouter_api_key
```

### Supported Categories
- electronics
- tv
- laptop
- phone / smartphones
- kitchen_appliances
- fashion
- groceries

### Default Parameters
Customize in `client/orchestrator.py`:
- Inventory levels: `current_stock`, `in_transit`
- Lead times: `lead_time_days`
- Price points: `default_prices` dict
- Safety stock multipliers

---

## 🎯 Use Cases

### Daily Operations
```bash
# Morning analysis
python cli.py batch electronics fashion groceries

# Category-specific deep dive
python cli.py analyze tv --days 60
```

### Automation
```python
# Scheduled analysis job
from client import batch_analysis
import asyncio

async def daily_report():
    results = await batch_analysis(["electronics", "fashion"])
    # Send to dashboard, email alerts, etc.
```

### API Integration
```python
# FastAPI endpoint
from fastapi import FastAPI
from client import RetailOpsClient

app = FastAPI()
client = RetailOpsClient()

@app.get("/analyze/{category}")
async def analyze(category: str):
    return await client.run_full_workflow(category)
```

---

## 📈 Performance

- **Single workflow**: 6-10 seconds (3 sequential server calls)
- **Batch processing**: 10-15 seconds for 3 categories (parallel)
- **Forecast only**: 2-3 seconds
- **Scalability**: Async/await with parallel execution

---

## 🐛 Troubleshooting

### Common Issues

**"Module not found"**
```bash
cd client && pip install -r requirements.txt
```

**"Server connection failed"**
1. Check `.env` file exists with `OPENROUTER_API_KEY`
2. Verify Python is in PATH
3. Ensure server files exist in `servers/` directories

**"No data for category"**
- Check category exists in `servers/forecasting/data/sales_history.csv`
- Supported: electronics, tv, laptop, phone, kitchen_appliances, fashion, groceries

**Detailed logs**
- Check stderr output for detailed debugging info
- All client operations log to stderr

---

## 🤝 Contributing

### Adding New Servers
1. Create server in `servers/your_server/`
2. Implement MCP protocol with FastMCP
3. Add to `MCPServerManager` in `orchestrator.py`
4. Add node to LangGraph workflow

### Extending Workflow
```python
# Add custom node
async def custom_node(state: RetailOpsState):
    # Your logic
    return state

workflow.add_node("custom", custom_node)
workflow.add_edge("price", "custom")
```

---

## 📄 License

Part of the RetailOps MCP project.

---

## 🙏 Acknowledgments

- **MCP Protocol**: [modelcontextprotocol.io](https://modelcontextprotocol.io)
- **LangGraph**: [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph)
- **OpenRouter**: [openrouter.ai](https://openrouter.ai)

---

## 📞 Support

- **Documentation**: See `/client/README.md` for detailed API docs
- **Examples**: Run `python examples.py --all` for usage patterns
- **Architecture**: See `ARCHITECTURE_DIAGRAM.md` for system design
- **Issues**: Check stderr logs for detailed error messages

---

## ✨ Quick Commands Cheat Sheet

```bash
# Test
python test_client.py

# Single analysis
python cli.py analyze tv

# Batch
python cli.py batch electronics fashion groceries

# Forecast only
python cli.py forecast laptop --days 60

# JSON output
python cli.py json phone > output.json

# Examples
python examples.py --all

# Integration test
python test_integration.py
```

---

**Status:** ✅ Production Ready  
**Version:** 1.0.0  
**Last Updated:** January 4, 2026

🚀 **Start analyzing your retail operations now!**

```bash
cd client && python test_client.py
```
