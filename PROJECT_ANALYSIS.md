# RetailOps MCP Project - Complete Analysis

**Analysis Date:** January 4, 2026  
**Analyzed by:** Claude (AI Assistant)

---

## 📋 Executive Summary

This is a **Model Context Protocol (MCP)** based retail operations system with 3 active AI-powered microservices that work together to optimize retail decision-making. The system uses **LangGraph** for complex reasoning workflows and **OpenRouter API** (with free Llama 3.1 8B model) for AI-powered narratives.

**Status:** ✅ All 3 servers are functional with test suites  
**Architecture:** MCP STDIO-based communication  
**AI Provider:** OpenRouter (Free tier - Llama 3.1 8B)

---

## 🏗️ System Architecture

```
RetailOps MCP System
│
├── 3 MCP Servers (STDIO Communication)
│   ├── 1. Forecasting Server
│   ├── 2. Replenishment Server
│   └── 3. Pricing Strategy Server
│
├── Client/Orchestrator (Empty - needs implementation)
├── UI (Empty - needs implementation)
└── Data Layer (JSON/CSV files)
```

---

## 🔧 Server Capabilities Deep Dive

### 1️⃣ FORECASTING SERVER (`servers/forecasting/`)

**Purpose:** Predicts future demand for product categories using historical data and seasonal events.

**Technology Stack:**
- FastMCP (MCP Server framework)
- Pandas (Data processing)
- OpenAI SDK (OpenRouter integration)
- Python-dotenv (Environment management)

**Core Algorithm:**
```
Final Forecast = Base Forecast × Seasonal Multiplier × Historical Surge Factor

Where:
- Base Forecast = 30-day simple moving average
- Seasonal Multiplier = Event-based multiplier (1.0-1.45)
- Historical Surge Factor = Category-specific surge profile
```

**Data Sources:**
1. **sales_history.csv** - Historical sales data (date, category, sales)
2. **events.json** - Upcoming events (Diwali: 1.45x, Christmas: 1.30x)
3. **surge_profile.json** - Category-specific surge multipliers by event
   - Example: TV during Diwali = 2.5x surge

**API Tool:**
```
getForecast(category: str, days_ahead: int = 30) -> dict
```

**Response Structure:**
```json
{
  "category": "tv",
  "base_forecast": 145.2,
  "seasonal_multiplier": 1.45,
  "historical_surge_factor": 2.5,
  "final_forecast": 526.35,
  "event": "Diwali",
  "narrative": "AI-generated explanation of forecast factors"
}
```

**Supported Categories:**
- electronics
- tv
- smartphones
- kitchen_appliances
- fashion

**Key Features:**
✅ Simple moving average baseline
✅ Event proximity detection (within 15 days)
✅ AI-powered narrative generation
✅ STDIO-safe logging to stderr
✅ Comprehensive test suite

**Strengths:**
- Simple and explainable algorithm
- Festival-aware forecasting (important for Indian retail)
- Good error handling

**Limitations:**
- No trend analysis or seasonality decomposition
- Fixed 30-day moving average (not adaptive)
- Limited to pre-configured events
- No machine learning models

---

### 2️⃣ REPLENISHMENT SERVER (`servers/replenishment/`)

**Purpose:** Recommends inventory restocking decisions using a multi-step reasoning graph.

**Technology Stack:**
- FastMCP (MCP Server)
- LangGraph (AI workflow orchestration)
- OpenAI SDK (OpenRouter)
- Python-dotenv

**Architecture:** Multi-node reasoning graph with 7 stages

**LangGraph Workflow:**
```
[demand_risk] → [festival] → [inventory] → [safety] → [reorder] → [timing] → [narrative]
```

**Node Breakdown:**

1. **demand_risk_node:**
   - Calculates volatility multiplier
   - low: 1.1x, medium: 1.25x, high: 1.4x

2. **festival_urgency_node:**
   - Checks if festival is within supplier lead time
   - Applies 1.2x multiplier if urgent

3. **inventory_runway_node:**
   - Calculates: runway_days = effective_stock / avg_daily_demand
   - effective_stock = current_stock + in_transit_stock

4. **safety_stock_node:**
   - Formula: avg_daily × lead_time × volatility × festival_multiplier

5. **reorder_decision_node:**
   - Calculates: demand + safety_stock - effective_stock
   - Enforces minimum order quantity (MOQ)

6. **timing_risk_node:**
   - immediate: runway < lead_time (high stockout risk)
   - soon: runway < 30 days (medium risk)
   - defer: runway >= 30 days (low risk)

7. **narrative_node:**
   - AI-generated explanation of decision

**API Tool:**
```
getReplenishmentDecision(input: dict) -> dict
```

**Input Schema:**
```json
{
  "category": "electronics",
  "forecast": {
    "forecasted_demand": 480,
    "avg_daily_demand": 16,
    "demand_volatility": "high|medium|low",
    "event": {"name": "Diwali", "days_to_event": 9}
  },
  "inventory": {
    "current_stock": 310,
    "in_transit_stock": 40
  },
  "supplier": {
    "lead_time_days": 10,
    "minimum_order_quantity": 50
  }
}
```

**Response Structure:**
```json
{
  "reorder_qty": 250,
  "reorder_timing": "immediate|soon|defer",
  "stockout_risk": "high|medium|low",
  "narrative": "AI explanation"
}
```

**Mock Test Cases:** 10 scenarios covering:
- Festival urgency situations
- Overstocking scenarios
- High volatility + low stock
- Various lead times and MOQs

**Strengths:**
- Sophisticated multi-factor reasoning
- LangGraph provides explainability through state transitions
- Festival-aware urgency logic
- Considers in-transit inventory

**Limitations:**
- No historical stockout data incorporation
- Fixed volatility multipliers (not learned)
- No supplier reliability scoring
- Simple safety stock calculation (could use more advanced methods)

---

### 3️⃣ PRICING STRATEGY SERVER (`servers/pricing-strategy/`)

**Purpose:** Recommends dynamic pricing adjustments based on inventory, demand, and competition.

**Technology Stack:**
- FastMCP
- LangGraph (3-node workflow)
- OpenAI SDK (OpenRouter)
- Python-dotenv

**LangGraph Workflow:**
```
[load] → [logic] → [narrative]
```

**Pricing Logic:**

1. **Load Node:**
   - Loads elasticity data
   - Loads competitor prices
   - Calculates inventory ratio

2. **Logic Node:**
   - **Clearance Mode** (inv_ratio > 2): 8% discount
   - **Premium Mode** (inv_ratio < 0.5): 5% markup
   - **Competitive Mode** (price > competitor × 1.1): 5% reduction
   - **Maintain Mode**: No change

3. **Narrative Node:**
   - AI explanation of pricing decision

**Data Sources:**

1. **price_elasticity.json:**
   - Elasticity coefficients (-0.8 to -2.0)
   - Base margins (15%-40%)
   - Max discount thresholds

2. **competitor_prices.json:**
   - Competitor average prices
   - Current price positioning
   - Price difference percentages

**API Tool:**
```
getPricingStrategy(input: dict) -> dict
```

**Input Schema:**
```json
{
  "category": "electronics",
  "current_price": 9000,
  "forecasted_demand": 150,
  "inventory_level": 200,
  "target_profit_pct": 5.0
}
```

**Response Structure:**
```json
{
  "category": "electronics",
  "recommended_price": 8550,
  "price_change_pct": -5.0,
  "recommendation_type": "competitive|clearance|premium|maintain",
  "narrative": "AI explanation"
}
```

**Supported Categories:**
- electronics (elasticity: -1.5)
- tv (elasticity: -1.8)
- laptop (elasticity: -1.3)
- phone (elasticity: -1.6)
- kitchen_appliances (elasticity: -1.4)
- fashion (elasticity: -2.0, highly elastic)
- groceries (elasticity: -0.8, inelastic)

**Strengths:**
- Competitor-aware pricing
- Inventory-driven adjustments
- Category-specific elasticity
- Simple rule-based logic (explainable)

**Limitations:**
- Doesn't actually use elasticity coefficients in calculations!
- No profit optimization algorithm
- Fixed threshold rules (not adaptive)
- No A/B testing framework
- No time-series price optimization

---

## 🔄 System Integration Flow

**Typical Workflow:**
```
1. Forecasting Server
   ↓ (forecasted_demand)
2. Replenishment Server
   ↓ (reorder_qty, timing)
3. Pricing Strategy Server
   ↓ (recommended_price)
4. [Missing] Orchestrator/Client
   ↓ (combined insights)
5. [Missing] UI/Dashboard
```

---

## 📊 Data Assets

### Sales History (forecasting/data/sales_history.csv)
- **Granularity:** Daily
- **Period:** September 2024 - Present
- **Categories:** electronics, tv, kitchen_appliances, smartphones, fashion
- **Format:** date, category, sales

### Events (forecasting/data/events.json)
- Diwali 2025: Oct 20 (1.45x multiplier)
- Christmas 2025: Dec 25 (1.30x multiplier)

### Surge Profiles (forecasting/data/surge_profile.json)
- Category-specific multipliers per event
- Example: TV during Diwali = 2.5x

### Price Elasticity (pricing-strategy/data/price_elasticity.json)
- Elasticity coefficients
- Margin constraints
- Discount limits

### Competitor Prices (pricing-strategy/data/competitor_prices.json)
- 7 categories tracked
- Price difference percentages
- Competitive positioning

---

## 🧪 Testing Infrastructure

### Forecasting Server
- **test_client.py** - MCP client integration test
- **test_comprehensive.py** - (exists but not reviewed)

### Replenishment Server
- **test_replenishment_graph.py** - Graph workflow tests
- **mock_replenishment_inputs.json** - 10 test scenarios

### Pricing Strategy Server
- **test_pricing.py** - 3 scenario tests (competitive, profit, clearance)
- **mock_pricing_inputs.json** - 7 category inputs

### Root Level
- **test_connection.py** - E2E connection test
- **test_connection_fixed.py** - (variant)

---

## 🚧 Missing Components

### 1. Client/Orchestrator (`client/` - EMPTY)
**Needed:**
- MCP client implementation
- Multi-server orchestration
- Workflow coordination
- Error handling and retries

**Suggested Implementation:**
- Use LangGraph for orchestration
- Create decision chains:
  - Forecast → Replenish → Price
  - Handle parallel calls for multiple categories
  - Aggregate results for dashboards

### 2. UI/Dashboard (`ui/` - EMPTY)
**Needed:**
- Web-based dashboard
- Real-time server status
- Decision visualization
- Data upload interface

**Suggested Stack:**
- React/Next.js frontend
- Recharts for visualization
- Tailwind CSS for styling
- WebSocket for real-time updates

### 3. Catalog Enricher (`servers/catalog_enricher/` - EMPTY)
**Appears to be a planned server, completely empty**

---

## 🔑 Environment Configuration

**Required Environment Variables:**
```env
OPENROUTER_API_KEY=sk-or-v1-xxxxx
```

**Current API Key:** ⚠️ EXPOSED in .env file (consider rotating)

**API Usage:**
- Model: meta-llama/llama-3.1-8b-instruct (FREE)
- Purpose: Narrative generation only
- Rate limits: OpenRouter free tier limits apply

---

## 💡 Improvement Opportunities

### High Priority

1. **Implement Client/Orchestrator**
   - Critical for end-to-end workflows
   - Needed for production use

2. **Build UI Dashboard**
   - Essential for business users
   - Visualization of decisions

3. **Fix Pricing Server Logic**
   - Actually use elasticity coefficients
   - Implement profit optimization
   - Add demand-based pricing

4. **Error Handling**
   - Add retry logic
   - Fallback mechanisms
   - Better error messages

### Medium Priority

5. **Enhanced Forecasting**
   - Add trend analysis
   - Seasonal decomposition
   - ML models (Prophet, ARIMA)

6. **Security**
   - Rotate exposed API key
   - Use environment-specific configs
   - Add authentication layer

7. **Data Quality**
   - Data validation
   - Anomaly detection
   - Missing data handling

8. **Testing**
   - Integration tests
   - Load testing
   - Edge case coverage

### Low Priority

9. **Monitoring**
   - Logging infrastructure
   - Performance metrics
   - Decision audit trail

10. **Documentation**
    - API documentation
    - Architecture diagrams
    - Deployment guide

---

## 🎯 Quick Wins

1. **Create end-to-end workflow script** (can demo system)
2. **Add input validation** (prevent bad data)
3. **Implement simple web UI** (makes system accessible)
4. **Add more test cases** (improve reliability)
5. **Document API contracts** (easier integration)

---

## 📈 Production Readiness Assessment

| Component | Status | Production Ready? | Blocker |
|-----------|--------|-------------------|---------|
| Forecasting Server | ✅ Working | ⚠️ Partial | Need better algorithms |
| Replenishment Server | ✅ Working | ⚠️ Partial | Need validation |
| Pricing Strategy Server | ✅ Working | ❌ No | Logic incomplete |
| Client/Orchestrator | ❌ Missing | ❌ No | Not implemented |
| UI/Dashboard | ❌ Missing | ❌ No | Not implemented |
| Catalog Enricher | ❌ Empty | ❌ No | Not started |

**Overall:** 🔶 **MVP Stage** - Core servers work, but missing critical integration layer

---

## 🚀 Recommended Next Steps

1. **Immediate (This Week):**
   - Implement basic orchestrator client
   - Create simple web UI for testing
   - Fix pricing server logic

2. **Short-term (This Month):**
   - Add comprehensive error handling
   - Implement data validation
   - Create deployment documentation

3. **Medium-term (Next Quarter):**
   - Enhance forecasting algorithms
   - Build production-grade UI
   - Add monitoring and logging

4. **Long-term (This Year):**
   - ML model integration
   - A/B testing framework
   - Multi-region support

---

## 📝 Technical Debt

1. Exposed API key in version control
2. No input validation on server tools
3. Hard-coded thresholds (not configurable)
4. Limited error handling
5. No rate limiting
6. No authentication/authorization
7. Elasticity data not actually used in pricing
8. No database (everything in JSON/CSV)
9. No caching layer
10. No CI/CD pipeline

---

## 🎓 Learning Observations

**Well Done:**
- Clean MCP server implementations
- Good use of LangGraph for reasoning
- STDIO-safe logging (critical for MCP)
- Comprehensive test cases
- Clear separation of concerns

**Needs Work:**
- Documentation (especially API contracts)
- Integration layer completely missing
- Production infrastructure
- Security best practices
- Data persistence strategy

---

## 🔗 Dependencies Summary

**Python Version:** 3.10+ (3.11+ for pricing server)

**Core Dependencies:**
- fastmcp >= 2.13.1 (all servers)
- langgraph >= 0.2.0 (replenishment, pricing)
- openai >= 2.8.1 (all servers)
- python-dotenv >= 1.2.1 (all servers)
- pandas >= 2.3.3 (forecasting)
- numpy >= 2.2.6 (forecasting)

---

## 📞 Support Resources

**Documentation:**
- MCP: https://modelcontextprotocol.io
- LangGraph: https://langchain-ai.github.io/langgraph
- OpenRouter: https://openrouter.ai/docs

**Project Files:**
- USAGE.md (comprehensive usage guide)
- Individual server README files
- Test scripts for each server

---

## End of Analysis

This is a solid foundation for a retail operations AI system. The core decision-making logic is implemented, but it needs integration and production-readiness work to be useful for actual business users.

**Overall Assessment:** 🟢 Good architecture, 🟡 Needs integration work, 🔴 Not production-ready

Would you like me to help with any specific component?
