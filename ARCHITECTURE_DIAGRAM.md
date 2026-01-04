# RetailOps MCP System - Visual Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    RETAILOPS MCP SYSTEM                             │
│                   LangGraph Orchestration                           │
└─────────────────────────────────────────────────────────────────────┘

                              USER INTERFACES
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   CLI Tool   │  │  Python API  │  │   Functions  │
    │  cli.py      │  │  Client()    │  │  full_...()  │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                  │                  │
           └──────────────────┼──────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  ORCHESTRATOR     │
                    │  (LangGraph)      │
                    │  orchestrator.py  │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │ NODE 1  │          │ NODE 2  │          │ NODE 3  │
   │FORECAST │  ──────> │REPLEN   │  ──────> │ PRICE   │
   └────┬────┘          └────┬────┘          └────┬────┘
        │                     │                     │
        │                     │                     │
   ┌────▼────────────┐   ┌───▼─────────────┐  ┌───▼──────────────┐
   │  FORECASTING    │   │ REPLENISHMENT   │  │  PRICING         │
   │  MCP SERVER     │   │ MCP SERVER      │  │  STRATEGY        │
   │                 │   │                 │  │  MCP SERVER      │
   │  • Moving Avg   │   │  • LangGraph    │  │  • LangGraph     │
   │  • Seasonal     │   │  • 7 Nodes      │  │  • 3 Nodes       │
   │  • Surge        │   │  • Safety Stock │  │  • Elasticity    │
   │  • AI Narrative │   │  • Risk Calc    │  │  • Competition   │
   └─────────────────┘   └─────────────────┘  └──────────────────┘
         │                       │                      │
         ▼                       ▼                      ▼
   ┌──────────┐          ┌──────────┐          ┌──────────┐
   │  DATA    │          │  DATA    │          │  DATA    │
   │ • sales  │          │ • mocks  │          │ • elast  │
   │ • events │          │          │          │ • comp   │
   │ • surge  │          │          │          │          │
   └──────────┘          └──────────┘          └──────────┘


                     STATE FLOW THROUGH WORKFLOW

Input State:
┌───────────────────────────────────────────────────────────┐
│ category: "tv"                                            │
│ days_ahead: 30                                            │
│ errors: []                                                │
│ workflow_status: "running"                                │
└───────────────────────────────────────────────────────────┘
                              │
                              ▼
After Forecast Node:
┌───────────────────────────────────────────────────────────┐
│ + forecast_data: {...}                                    │
│ + base_forecast: 145.2                                    │
│ + final_forecast: 526.35                                  │
│ + seasonal_multiplier: 1.45                               │
│ + event: "Diwali"                                         │
│ + forecast_narrative: "AI explanation..."                 │
└───────────────────────────────────────────────────────────┘
                              │
                              ▼
After Replenishment Node:
┌───────────────────────────────────────────────────────────┐
│ + replenishment_data: {...}                               │
│ + reorder_qty: 250                                        │
│ + reorder_timing: "immediate"                             │
│ + stockout_risk: "high"                                   │
│ + replenishment_narrative: "AI explanation..."            │
└───────────────────────────────────────────────────────────┘
                              │
                              ▼
After Pricing Node:
┌───────────────────────────────────────────────────────────┐
│ + pricing_data: {...}                                     │
│ + current_price: 28000                                    │
│ + recommended_price: 26600                                │
│ + price_change_pct: -5.0                                  │
│ + recommendation_type: "competitive"                      │
│ + pricing_narrative: "AI explanation..."                  │
│ workflow_status: "completed"                              │
└───────────────────────────────────────────────────────────┘


              COMPLETE WORKFLOW EXECUTION FLOW

1. USER REQUEST
   ↓
   "Analyze TV category for next 30 days"

2. CLIENT INITIALIZATION
   ↓
   RetailOpsClient() → Build LangGraph → Initialize State

3. FORECASTING NODE
   ↓
   • Connect to forecasting MCP server via STDIO
   • Call getForecast("tv", 30)
   • Receive: base=145.2, final=526.35, event=Diwali
   • Update state with forecast data
   ↓
   State: + forecast_data

4. REPLENISHMENT NODE
   ↓
   • Connect to replenishment MCP server via STDIO
   • Build input: forecast + inventory levels
   • Call getReplenishmentDecision(input)
   • Receive: reorder=250, timing=immediate, risk=high
   • Update state with replenishment data
   ↓
   State: + forecast_data + replenishment_data

5. PRICING NODE
   ↓
   • Connect to pricing MCP server via STDIO
   • Build input: forecast + current price + inventory
   • Call getPricingStrategy(input)
   • Receive: price=26600, change=-5%, type=competitive
   • Update state with pricing data
   ↓
   State: + forecast + replenishment + pricing

6. FINAL RESULT
   ↓
   {
     "category": "tv",
     "status": "completed",
     "forecast": {...},
     "replenishment": {...},
     "pricing": {...}
   }


                    DATA FLOW DIAGRAM

┌─────────────┐
│ sales_      │
│ history.csv ├──┐
└─────────────┘  │
                 │     ┌──────────────┐
┌─────────────┐  ├────►│ FORECASTING  │
│ events.json ├──┤     │    SERVER    │
└─────────────┘  │     └──────┬───────┘
                 │            │
┌─────────────┐  │            │ forecast_data
│ surge_      ├──┘            │
│ profile.json│               ▼
└─────────────┘     ┌──────────────────┐
                    │ REPLENISHMENT    │◄─── inventory levels
                    │     SERVER       │
                    └────────┬─────────┘
                             │
                             │ reorder_qty, timing
                             │
                             ▼
┌─────────────┐    ┌──────────────────┐
│ price_      │───►│    PRICING       │◄─── forecasted_demand
│ elasticity  │    │    SERVER        │
└─────────────┘    └────────┬─────────┘
                             │
┌─────────────┐             │
│ competitor_ │─────────────┘
│ prices      │              │
└─────────────┘              │
                             ▼
                    ┌──────────────────┐
                    │  FINAL RESULT    │
                    │  • Forecast      │
                    │  • Replenishment │
                    │  • Pricing       │
                    └──────────────────┘


                    USAGE PATTERNS

PATTERN 1: CLI (Quick Analysis)
┌─────────────────────────────────────────┐
│ $ python cli.py analyze tv              │
│                                         │
│ Output: Pretty-printed results          │
└─────────────────────────────────────────┘

PATTERN 2: Python Script (Automation)
┌─────────────────────────────────────────┐
│ from client import full_retail_analysis │
│                                         │
│ result = await full_retail_analysis()  │
│ # Process result...                     │
└─────────────────────────────────────────┘

PATTERN 3: Client API (Advanced)
┌─────────────────────────────────────────┐
│ client = RetailOpsClient()              │
│                                         │
│ # Single category                       │
│ result = await client.run_full_...()   │
│                                         │
│ # Batch processing                      │
│ results = await client.run_batch_...() │
│                                         │
│ # Forecast only                         │
│ forecast = await client.run_fore...()  │
└─────────────────────────────────────────┘

PATTERN 4: Batch Processing
┌─────────────────────────────────────────┐
│ categories = ["tv", "laptop", "phone"]  │
│                                         │
│ results = await batch_analysis(cats)   │
│                                         │
│ # All run in parallel                   │
└─────────────────────────────────────────┘


                  ERROR HANDLING FLOW

┌──────────────┐
│ Start Node   │
└──────┬───────┘
       │
       ▼
   Try Execute
       │
   ┌───┴────┐
   │        │
Success   Error
   │        │
   │        ▼
   │   state["errors"].append(error)
   │   state["status"] = "failed_X"
   │        │
   │        ▼
   │   Continue/Stop based on severity
   │        │
   └────┬───┘
        │
        ▼
  Return State
  (with partial results)


              MCP SERVER CONNECTION

Client                          Server
  │                               │
  ├──1. Start subprocess──────────►│
  │   (python server.py)          │
  │                               │
  ├──2. STDIO connection──────────►│
  │   (stdin/stdout)              │
  │                               │
  ├──3. Initialize session────────►│
  │                               │
  ├──4. Call tool────────────────►│
  │   (getForecast, etc.)         │
  │                               │
  │◄─5. JSON response─────────────┤
  │                               │
  ├──6. Parse & update state      │
  │                               │
  ├──7. Close connection──────────►│
  │                               │
  └──8. Cleanup subprocess────────►│


          PERFORMANCE CHARACTERISTICS

Single Workflow (3 servers sequential):
┌────────────────────────────────┐
│ Forecast:      2-3 seconds     │
│ Replenishment: 2-3 seconds     │
│ Pricing:       2-3 seconds     │
│ ────────────────────────────   │
│ Total:         6-10 seconds    │
└────────────────────────────────┘

Batch Processing (N categories parallel):
┌────────────────────────────────┐
│ 1 category:   6-10 seconds     │
│ 3 categories: 10-15 seconds    │
│ 5 categories: 12-18 seconds    │
│                                │
│ (Parallel execution scales)    │
└────────────────────────────────┘


This visual guide shows how everything connects!
The LangGraph orchestrator efficiently chains all servers
while maintaining clean state and error handling.
```
