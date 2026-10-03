# RetailOps Common Evaluation Specification and Environment Freeze

**Document ID**: `SPEC-EVAL-FROZEN-V1`  
**Date**: October 3, 2026  
**Status**: FROZEN (Baseline specification for upcoming experimental steps 3–12)  
**Target Repository**: `E:\Repositories\RetailOPS-MCP`  
**Applicability**: 
- Experiment A: Model Replacement (Statistical/ML forecasting swap)
- Experiment B: M5/Walmart Operational Simulation
- Experiment C: Same-Repository Comparison (RetailOps vs. Reproduced Architectures)
- Experiment D: Human-in-the-Loop (HITL) Governance & Approval Evaluation

---

## 1. Executive Summary & Purpose

The purpose of this specification is to freeze the evaluation environment, data contracts, operational scenarios, quantitative metrics, and fair-comparison rules across the RetailOps research project before running new experiments.

In accordance with academic evaluation standards:
1. **Separation of Architectural Metrics from Algorithmic Performance**: Software engineering metrics (lines of code churn, subprocess spawn latency, interface stability, failure boundary containment) are evaluated independently from retail domain algorithm metrics (MAE, RMSE, stockout rate, holding cost).
2. **Deterministic Reproducibility**: Input series, catalog configurations, operational disturbance profiles, and random seeds are frozen.
3. **Common Ground**: All evaluated architectures (RetailOps, in-process baseline, reproduced external architectural patterns, and HITL variants) must execute against identical datasets, identical operational scenarios, and identical evaluation criteria.

---

## 2. Data Staging & Versioning

### 2.1 Frozen Prototype Dataset (Current Local Evaluation)
The existing synthetic retail dataset located in `servers/*/data/` and documented in [`DATA_SPECIFICATION.md`](file:///E:/Repositories/RetailOPS-MCP/DATA_SPECIFICATION.md) is **frozen** and must remain unchanged for prototype and baseline tests:
- **Catalog & Categories**: 7 retail categories (`tv`, `laptop`, `phone`, `kitchen_appliances`, `fashion`, `groceries`, `electronics`) in `servers/catalog-enricher/data/product_catalog.json` and `category_mappings.json`.
- **Sales History**: `servers/forecasting/data/sales_history.csv` (10,950 daily records across categories from 2021 to 2023).
- **Calendar & Surges**: `servers/forecasting/data/events.json` and `servers/forecasting/data/surge_profile.json` (Diwali, Christmas seasonal multipliers).
- **Pricing & Elasticity**: `servers/pricing-strategy/data/price_elasticity.json` and `competitor_prices.json`.
- **Supplier Directory**: Deterministic catalog in `servers/supplier-intelligence/server.py` and `baseline/supplier_intelligence.py`.

### 2.2 Staging Location for Future M5 / Walmart Dataset
When ingested in future steps, external benchmark datasets will be staged in dedicated subdirectories under `data/`:
- **Directory Path**: `data/m5/`
  - `data/m5/raw/`: Original competition CSVs (`sales_train_evaluation.csv`, `calendar.csv`, `sell_prices.csv`).
  - `data/m5/processed/`: Standardized category and SKU time-series mapped to the RetailOps schema.
- **Rule**: No M5 files are created or altered during this freeze step.

---

## 3. Standardized Forecasting Tool Contract

Both the current moving average servers and any future statistical/ML forecasting models (e.g. ARIMA, LightGBM) must strictly adhere to the standardized FastMCP tool contract.

### 3.1 Tool Identifier & Transport
- **Tool Name**: `getForecast`
- **Transport**: Standard I/O (`stdio`) JSON-RPC 2.0 over FastMCP (or equivalent direct function call for in-process baselines).

### 3.2 Input Contract (JSON Schema)
```json
{
  "type": "object",
  "properties": {
    "category": {
      "type": "string",
      "description": "Retail product category identifier (e.g. 'tv', 'electronics', 'fashion')"
    },
    "days_ahead": {
      "type": "integer",
      "default": 30,
      "minimum": 1,
      "maximum": 365,
      "description": "Forecast horizon in days"
    },
    "series_id": {
      "type": "string",
      "description": "Optional specific SKU or store series ID (used in M5 evaluation)"
    }
  },
  "required": ["category"]
}
```

### 3.3 Output Contract (JSON Schema)
```json
{
  "type": "object",
  "properties": {
    "category": { "type": "string" },
    "base_forecast": { "type": "number", "description": "Baseline demand prediction before exogenous multipliers" },
    "seasonal_multiplier": { "type": "number", "description": "Calendar or event adjustment factor (>= 0.0)" },
    "historical_surge_factor": { "type": "number", "description": "Empirical category surge multiplier (>= 0.0)" },
    "final_forecast": { "type": "number", "description": "Final predicted demand units over the requested horizon" },
    "event": { "type": ["string", "null"], "description": "Name of upcoming event or null" },
    "narrative": { "type": "string", "description": "Human-readable explanation of forecast derivation" },
    "model_metadata": {
      "type": "object",
      "properties": {
        "model_type": { "type": "string" },
        "training_horizon_days": { "type": "integer" }
      }
    }
  },
  "required": [
    "category",
    "base_forecast",
    "seasonal_multiplier",
    "historical_surge_factor",
    "final_forecast",
    "event",
    "narrative"
  ]
}
```

---

## 4. Fixed Operational Scenarios

To ensure comparable, reproducible evaluation across all system architectures, a fixed set of **5 operational scenarios** is defined:

| Scenario ID | Scenario Name | Injected Operational Condition | Target State Variables & Parameter Modifications | Expected Downstream Impact |
| :--- | :--- | :--- | :--- | :--- |
| **SCEN-01** | **Normal Demand** | Baseline steady-state operations; historical sales within 1 standard deviation; standard supplier lead time (7 days). | `volatility: "low"`, `event: None`, `lead_time_days: 7`, `current_stock: 100`, `in_transit: 50`. | Stable stock runway; routine reorder quantity; maintain base pricing. |
| **SCEN-02** | **Demand Spike** | Exogenous surge event within lead-time window (e.g. major festival or promotion); 2.0x–3.0x multiplier on base sales. | `volatility: "high"`, `event: "Diwali" (multiplier: 1.45, surge: 2.5x)`, `days_to_event: 15`, `lead_time_days: 14`. | Safety stock escalation; accelerated reorder urgency; potential price optimization. |
| **SCEN-03** | **Low Inventory** | On-hand inventory depleted below safety threshold due to prior demand or defective batch. | `current_stock: 10`, `in_transit: 0`, `avg_daily_demand: 15`, `lead_time_days: 7` (runway < 1 day). | Immediate stockout warning (`stockout_risk: "high"`); emergency reorder triggered. |
| **SCEN-04** | **Supplier Delay** | Supplier lead time doubled due to logistics congestion or route disruption; reliability score downgraded. | `lead_time_days: 21` (up from 7), `supplier_reliability_score: 0.65`, `disrupted_route: True`. | Extended required buffer stock; earlier reorder point; vendor risk escalation. |
| **SCEN-05** | **Stockout-Risk Situation** | Compound stress: Demand surge coincides with depleted inventory and extended supplier lead time. | `current_stock: 5`, `in_transit: 0`, `demand_multiplier: 2.5`, `lead_time_days: 14`, `days_to_event: 10`. | Severe stockout prediction; maximum replenishment order; critical executive decision gate. |

---

## 5. Common Metrics Hierarchy

Metrics are organized into four explicit categories. Each metric is designated as either **[AUDITED]** (already measured in prior tasks) or **[PLANNED]** (to be computed during Steps 3–12).

### 5.1 Forecasting Quality Metrics
- **Mean Absolute Error (MAE)** `[PLANNED - PRIMARY]`:
  $$\text{MAE} = \frac{1}{H} \sum_{t=1}^H |y_t - \hat{y}_t|$$
  *Primary accuracy metric. Measured in physical units (SKU volume). Scale-dependent.*
- **Root Mean Squared Error (RMSE)** `[PLANNED - SECONDARY]`:
  $$\text{RMSE} = \sqrt{\frac{1}{H} \sum_{t=1}^H (y_t - \hat{y}_t)^2}$$
  *Penalizes large outlier forecast errors.*
- **Mean Absolute Percentage Error (MAPE)** `[PLANNED - SECONDARY]`:
  $$\text{MAPE} = \frac{100\%}{H} \sum_{t=1}^H \left|\frac{y_t - \hat{y}_t}{y_t}\right| \quad (y_t \ne 0)$$

### 5.2 Operational & Supply Chain Metrics
- **Stockout Rate (%)** `[PLANNED - PRIMARY]`:
  $$\text{Stockout Rate} = \frac{\sum_{t=1}^H \mathbb{I}(I_t = 0 \land d_t > 0)}{H} \times 100\%$$
- **Service Level (%)** `[PLANNED - PRIMARY]`:
  $$\text{Service Level} = \frac{\sum_{t=1}^H \min(d_t, I_t)}{\sum_{t=1}^H d_t} \times 100\%$$
- **Inventory Holding Cost ($/₹)** `[PLANNED]`: Cumulative cost of carrying on-hand inventory across horizon $H$, calculated as $\sum_{t=1}^H (I_t \times c_{unit} \times h_{rate})$.
- **Replenishment Reorder Cost ($/₹)** `[PLANNED]`: Total procurement expense based on units ordered and supplier cost index.
- **Constraint Violations** `[PLANNED]`: Count of orders exceeding supplier minimum/maximum lot sizes or store capacity limits.

### 5.3 Modularity & Systems Engineering Metrics
- **Existing Service Files Modified** `[AUDITED]`: Files modified in existing microservices (Target: 0).
- **Existing Service LOC Modified** `[AUDITED]`: Lines of code modified in existing domain services (Target: 0).
- **Orchestration LOC Added/Modified** `[AUDITED]`: Churn localized strictly to the workflow client.
- **Interface Contract Adherence (%)** `[AUDITED]`: Percentage of schema fields preserved across service replacement or extension ($100\%$).
- **Pipeline Latency (ms)** `[AUDITED]`: Mean, Median, and P95 latency (comparing in-process, process-per-call, and persistent MCP session pool).

### 5.4 Human-in-the-Loop (HITL) Governance Metrics
- **Approval Rate (%)** `[PLANNED]`:
  $$\text{Approval Rate} = \frac{N_{\text{approved}}}{N_{\text{total decisions}}} \times 100\%$$
- **Override Rate (%)** `[PLANNED]`:
  $$\text{Override Rate} = \frac{N_{\text{overridden}}}{N_{\text{total decisions}}} \times 100\%$$
- **Approval Latency / Time-to-Decision (s)** `[PLANNED]`: Duration an operational decision remains suspended in the human gate before approval or rejection.
- **Escalation Count** `[PLANNED]`: Frequency with which automated safety checks route decisions to senior supervisors (e.g. reorders exceeding ₹100,000 or price cuts > 20%).
- **Policy / Constraint Violations Prevented** `[PLANNED]`: Frequency with which the human gate prevented an erroneous or out-of-bounds agent action.

---

## 6. Fair-Comparison Rules

To ensure an academically rigorous comparison between RetailOps and alternative architectures (in-process monolith, paper-derived architectures, or fully autonomous vs. HITL pipelines), the following rules are **frozen**:

1. **Identical Historical Horizon & Test Splits**:
   All models and architectures evaluate the exact same time intervals. No architecture may access future calendar or sales data before its simulated time step $t$.
2. **Fixed Upstream Data Feeds**:
   When comparing orchestration architectures (e.g. MCP vs. in-process vs. WorkflowLLM/Flowr representations), the underlying domain inputs (catalog attributes, pricing elasticity tables, historical sales) must be identical bit-for-bit.
3. **Hardware & Process Boundary Controls**:
   All latency benchmarks must record execution on the same physical host machine, using the same Python runtime, under explicit isolation modes (process-per-call vs. persistent pool).
4. **Deterministic Simulation Seed**:
   Any stochastic elements (e.g. supplier delivery jitter, demand shocks) must use a fixed random seed (`RANDOM_SEED = 42`).
5. **Separation of Concerns**:
   No claim may be made that RetailOps possesses higher retail forecasting accuracy simply because it utilizes MCP for process orchestration. Architectural benefits must be evidenced strictly by software engineering and operational reliability metrics.

---

## 7. Consistency Verification Across Planned Experiments

| Experiment | Frozen Specification Element Applied | Verification Status |
| :--- | :--- | :--- |
| **A. Model Replacement** | `getForecast` tool schema (Section 3); Integration effort metrics (Section 5.3); MAE/RMSE metrics (Section 5.1). | **Consistent**: Statistical models plug into the existing `getForecast` contract; LOC churn is evaluated against zero-service-modification targets. |
| **B. M5 Operational Evaluation** | Data staging directory `data/m5/` (Section 2.2); Scenarios SCEN-01 through SCEN-05 (Section 4); Stockout rate & service level (Section 5.2). | **Consistent**: Standardized 5 scenarios translate directly into M5 store/SKU series with realistic inventory simulations. |
| **C. Same-Repository Architecture Comparison** | Fair-comparison rules (Section 6); Modularity & systems metrics (Section 5.3); Scenarios SCEN-01 to SCEN-05 (Section 4). | **Consistent**: Reproduced architectures execute the exact same 5 operational scenarios under identical fair-comparison rules. |
| **D. Human-in-the-Loop Evaluation** | HITL metrics (Section 5.4); Scenarios SCEN-03 & SCEN-05 (Section 4); Approval & escalation policies. | **Consistent**: HITL approval gates evaluate high-risk scenarios (SCEN-03 low inventory, SCEN-05 compound risk) measuring approval rate and prevention of constraint violations. |

---

## 8. Unresolved Decisions & Limitations

1. **M5 Aggregation Level**:
   Whether M5 series will be evaluated at the aggregate category level (matching the current 7 categories) or at individual store-SKU level is deferred to Step 4/Step 5 implementation. The staging directory `data/m5/` accommodates both.
2. **LLM Non-Determinism in HITL**:
   For narrative generation and natural language query interpretation, external LLM calls introduce minor latency and wording variance. In benchmark tests, mock-deterministic services or temperature $0.0$ should be enforced to eliminate non-deterministic variance.
3. **OS-Specific Subprocess Latency**:
   On Windows (`nt`), process spawning overhead is substantially higher than Unix `fork()`. The specification mandates explicitly reporting the host environment and reporting persistent session benchmarks alongside process-per-call.
