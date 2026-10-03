# RetailOps Frozen Experimental Protocol

**Document ID**: `PROTOCOL-EXP-FROZEN-V1`  
**Date**: October 3, 2026  
**Status**: FROZEN (Operational specification for upcoming experimental steps 4 through 12)  
**Target Repository**: `E:\Repositories\RetailOPS-MCP`  
**Applicability**: 
- Model Replacement Evaluation
- M5 Operational Simulation & Evaluation
- Same-Repository Architecture Comparison
- Human-in-the-Loop (HITL) Governance Evaluation

---

## 1. Executive Overview & Guiding Principles

This document specifies the frozen execution protocol for conducting four empirical experiments within the RetailOps repository. The goal is to produce verifiable, reproducible, and methodologically sound evidence regarding enterprise AI decision orchestration.

### Core Principles
1. **Separation of Architectural Effort from Algorithmic Accuracy**:
   - Modularity metrics (source code churn, interface stability, zero-modification blast radius) are measured independently from retail forecasting accuracy (MAE, RMSE, MAPE).
   - Higher forecasting accuracy does not prove superior architectural modularity, nor does architectural decoupling imply superior retail optimization.
2. **Deterministic Baseline Controls**:
   - All evaluated architectures, pipelines, and scenarios consume identical input records bit-for-bit.
   - Any synthetic disturbances or simulation loops must utilize the frozen random seed (`RANDOM_SEED = 42`).
3. **Pre-Registered Evaluation Rules**:
   - No scenarios, metrics, parameters, or evaluation horizons may be modified after observing results.

---

## 2. Experiment 1: Model Replacement Protocol

### 2.1 Implementations Under Evaluation
* **Baseline Forecasting Implementation**: Current 30-day Simple Moving Average (SMA) baseline service (`servers/forecasting/server.py`), computing moving average demand adjusted by seasonal event multipliers and historical surge profiles.
* **Replacement Forecasting Implementation**: A dedicated statistical/ML time-series model (e.g., AutoARIMA, Exponential Smoothing, or LightGBM) to be deployed as an independent service without modifying existing sibling services.

### 2.2 Input Data & Horizon
* **Input Dataset**: Historical category sales data (`servers/forecasting/data/sales_history.csv`) and calendar events (`events.json`, `surge_profile.json`).
* **Evaluation Horizon**: $H = 30$ days (fixed across all categories).
* **Train / Test Split**: First 80% of daily observations per category allocated to model training/fitting; final 20% reserved for out-of-sample forecast accuracy evaluation.

### 2.3 Outputs to Compare
Both baseline and replacement implementations must emit the identical standardized FastMCP output schema:
```json
{
  "category": "string",
  "base_forecast": "number",
  "seasonal_multiplier": "number",
  "historical_surge_factor": "number",
  "final_forecast": "number",
  "event": "string | null",
  "narrative": "string"
}
```

### 2.4 Forecasting Accuracy Calculation Procedure
For each category $c$ over the test evaluation horizon $H$:
1. **Mean Absolute Error (MAE - Primary)**:
   $$\text{MAE}_c = \frac{1}{H}\sum_{t=1}^H |y_{c,t} - \hat{y}_{c,t}|$$
2. **Root Mean Squared Error (RMSE - Secondary)**:
   $$\text{RMSE}_c = \sqrt{\frac{1}{H}\sum_{t=1}^H (y_{c,t} - \hat{y}_{c,t})^2}$$
3. **Mean Absolute Percentage Error (MAPE - Secondary)**:
   $$\text{MAPE}_c = \frac{100\%}{H}\sum_{t=1}^H \left|\frac{y_{c,t} - \hat{y}_{c,t}}{y_{c,t}}\right| \quad (y_{c,t} \ne 0)$$

### 2.5 Modularity & Systems Engineering Measurements
* **Existing Service Files Modified**: Total count of files changed across existing services (`catalog-enricher`, `replenishment`, `pricing-strategy`, `supplier-intelligence`). Target: `0`.
* **Existing Service LOC Modified**: Total lines of code modified inside existing service files. Target: `0`.
* **New Service LOC**: Total lines of code in the newly introduced replacement service file.
* **Orchestration LOC Changed**: Total lines modified or added in the orchestration runner (`client/orchestrator.py` or configuration maps).
* **Schema Compatibility**: Verification that 100% of required schema keys are present and conform to type constraints.
* **Orchestration Modification Determination**: Static git diff inspection. If the change only requires pointing a server path parameter (e.g. `RETAILOPS_FORECASTING_SERVER_PATH`) to the new server executable, orchestration logic churn is classified as configuration-only ($\le 1$ LOC).
* **Success Criteria for Contract-Preserving Replacement**:
  1. Zero lines of code modified in existing sibling services (`catalog-enricher`, `replenishment`, `pricing-strategy`).
  2. Downstream replenishment and pricing services execute to completion using replacement outputs without schema conversion errors.
  3. 100% of required output schema fields successfully populated.

---

## 3. Experiment 2: M5 Operational Simulation Protocol

### 3.1 End-to-End Simulation Pipeline Flow
```
M5 Dataset (data/m5/raw)
    │
    ▼
[Preprocessing & Aggregation] ──> Standardized Daily Category/SKU Time Series
    │
    ▼
[Forecasting Service] ──────────> Final Forecast Demand (Units over Horizon H)
    │
    ▼
[Inventory Initialization] ─────> On-Hand Stock (I_0) & Pipeline Orders (In-Transit)
    │
    ▼
[Supplier Parameters] ──────────> Lead Time (L), Minimum Order Qty (MOQ), Unit Cost
    │
    ▼
[Scenario Injection] ───────────> Disturbance Multipliers (Normal, Spike, Delay, etc.)
    │
    ▼
[Replenishment Decision] ───────> Recommended Reorder Quantity (Q_t) & Timing
    │
    ▼
[Inventory Simulation Engine] ──> Daily State Updates (Receipts, Sales, Stockouts)
    │
    ▼
[Metric Calculation] ───────────> Stockout Rate, Service Level, Holding & Reorder Costs
```

### 3.2 Evaluation Horizon & Unit of Evaluation
* **Evaluation Horizon**: $H = 28$ days (standard M5 competition evaluation window).
* **Unit of Evaluation**: Daily operational inventory periods ($t = 1, \dots, 28$) across selected standardized retail series (spanning Food/Grocery, Household, and Hobbies/General categories).
* **Train / Test Separation**: Historical sales prior to day $d - 28$ allocated to training; days $[d-27, d]$ reserved for operational rolling simulation.

### 3.3 Demand Translation & Operational Simulation Mechanics
* **Operational Inventory Demand**: At each day $t$, actual simulated demand $d_t$ is drawn from the ground-truth test split.
* **Inventory Initialization ($I_0$)**: Initial on-hand inventory configured as:
  $$I_0 = \text{round}(k_{\text{init}} \times \bar{d}_{\text{daily}} \times L)$$
  where $\bar{d}_{\text{daily}}$ is historical mean daily demand, $L$ is lead time, and $k_{\text{init}}$ is a configurable inventory coverage parameter (default: $1.0$; low inventory scenario: $0.2$).
* **Lead Time ($L$)**: Configurable parameter in days (default: $L = 7$ days; supplier delay scenario: $L = 21$ days).
* **Minimum Order Quantity (MOQ)**: Configurable batch constraint (default: $\text{MOQ} = 50$ units). Reorder quantities must satisfy $Q_t = 0$ or $Q_t \ge \text{MOQ}$.
* **Inventory Balance Equation**:
  $$I_t = \max(0, I_{t-1} + R_t - d_t)$$
  where $R_t$ represents supplier receipts arriving at day $t$ from orders placed at day $t - L$.
* **Stockout Handling**: Unfulfilled demand in period $t$ ($\max(0, d_t - (I_{t-1} + R_t))$) is recorded as lost sales (non-backlogged).

### 3.4 Operational Cost & Service Level Definitions
* **Holding Cost ($C_{\text{hold}}$)**:
  $$C_{\text{hold}} = \sum_{t=1}^H I_t \times c_{\text{unit}} \times h_{\text{rate}}$$
  where $c_{\text{unit}}$ is item unit cost and $h_{\text{rate}}$ is daily holding cost rate (configurable parameter, default: $0.001$ or $0.1\%$ per day).
* **Procurement / Reorder Cost ($C_{\text{order}}$)**:
  $$C_{\text{order}} = \sum_{t=1}^H \left(Q_t \times c_{\text{unit}} \times \text{cost\_index} + \mathbb{I}(Q_t > 0) \times S_{\text{order}}\right)$$
  where $S_{\text{order}}$ is fixed administrative ordering cost (configurable parameter, default: $0.0$).
* **Stockout Rate (%)**:
  $$\text{Stockout Rate} = \frac{\sum_{t=1}^H \mathbb{I}(I_t = 0 \land d_t > 0)}{H} \times 100\%$$
* **Service Level (%)**:
  $$\text{Service Level} = \frac{\sum_{t=1}^H \min(d_t, I_{t-1} + R_t)}{\sum_{t=1}^H d_t} \times 100\%$$

---

## 4. Experiment 3: Same-Repository Architecture Comparison Protocol

### 4.1 Selection Criteria for Published Reference Architectures
To ensure fair, defensible comparison, up to 3 candidate systems from literature will be selected strictly according to:
1. **Reproducibility**: Architectural workflow, tool interfaces, and agent roles must be clearly described in the source publication.
2. **Operational Relevance**: Directly addresses retail forecasting, replenishment, or decision orchestration.
3. **Repository Implementability**: Capable of execution within the existing local Python runtime without requiring proprietary closed-source enterprise software or undisclosed fine-tuned weights.
4. **Interface Isolation**: Implementable as standalone orchestrators consuming the exact same frozen retail datasets and tool interfaces.

*Rule: Complex proprietary frameworks with unreleased artifacts will not be chosen over clean, reproducible architectures.*

### 4.2 Candidate External Systems & Characterization
Based on the literature review conducted in earlier investigations:
1. **Flowr Pattern (Bandara et al., 2026, arXiv:2604.05987)**:
   - *Source*: Flowr enterprise retail framework.
   - *Reproducible Components*: MCP-based tool encapsulation; centralized reasoning coordinator routing requests to specialized services.
   - *Non-Reproducible Components*: Proprietary commercial fine-tuned specialist LLM weights; private enterprise cloud deployment infrastructure.
   - *Harness Adaptation*: Centralized LLM-driven dispatching agent invoking the standardized FastMCP tools over local stdio.
2. **WorkflowLLM Pattern (Reference literature architecture)**:
   - *Source*: WorkflowLLM workflow orchestration literature.
   - *Reproducible Components*: Explicit prompt-driven workflow generation; static step-by-step procedural execution graph.
   - *Non-Reproducible Components*: External proprietary workflow databases or proprietary benchmark datasets.
   - *Harness Adaptation*: Static procedural execution pipeline driving sequential service calls with prompt-based chaining.
3. **Agentic Replenishment Pattern (Autonomous single-domain literature architecture)**:
   - *Source*: Agentic AI framework for inventory replenishment.
   - *Reproducible Components*: Direct inventory-centric agent coordinating forecast and replenishment without multi-stage catalog enrichment or dynamic pricing loops.
   - *Non-Reproducible Components*: Proprietary ERP-specific database connectors.
   - *Harness Adaptation*: Focused 2-stage (Forecast $\rightarrow$ Replenish) autonomous agent loop.

### 4.3 Fair Comparison Protocol
* **Identical Inputs**: All architectures receive the identical product catalog, historical sales window, and scenario disturbance parameters.
* **Interface Isolation**: Each architecture resides in its own isolated subpackage (`experiments/same_repo_comparison/`).
* **Adapter Constraint**: Adapters are restricted solely to converting internal representation to the common evaluation harness output schema. No architecture receives custom parameter tuning denied to others.

---

## 5. Experiment 4: Human-in-the-Loop (HITL) Governance Protocol

### 5.1 Architectural Modes Under Comparison
* **Mode A (Fully Autonomous)**: End-to-end execution without human intervention. Orchestrator executes `enrich` $\rightarrow$ `forecast` $\rightarrow$ `replenish` $\rightarrow$ `price` and immediately commits decisions (e.g. generates purchase orders and applies pricing).
* **Mode B (Human-Supervised Decision Flow)**: Orchestrator executes autonomous stages but suspends state execution at designated governance checkpoints pending human inspection, approval, modification, or rejection.

### 5.2 Approval Gates & Governance Policies
* **Interception Checkpoints**:
  1. **Post-Replenishment Gate**: Triggered prior to purchase order creation if:
     - Reorder expenditure exceeds budget threshold ($Q_t \times c_{\text{unit}} > \text{BUDGET\_THRESHOLD}$, configurable: ₹100,000).
     - Stockout risk is classified as `"high"`.
     - Order quantity exceeds $2.5\times$ historical safety stock.
  2. **Post-Pricing Gate**: Triggered prior to POS price updates if:
     - Recommended price change percentage $| \Delta P | > 15\%$.
     - Recommended price falls below wholesale procurement cost (negative gross margin).
* **Human Operator Presentation**:
  When suspended, the state checkpoint surfaces:
  - Product identity, category, and historical velocity.
  - Model forecast, confidence interval, and narrative explanation.
  - Proposed reorder quantity, calculated stock runway, and supplier lead time.
  - Proposed price adjustment, competitor benchmark, and expected margin impact.
* **Operator Actions & State Transitions**:
  1. `APPROVE`: Proposed action accepted as generated; workflow resumes execution to next node.
  2. `OVERRIDE`: Operator inputs modified values (e.g., adjusts $Q$ from $600$ to $400$ units, or overrides price discount); workflow records override delta and resumes with adjusted values.
  3. `REJECT`: Proposed action cancelled; workflow logs rejection, sets safe fallback state, and aborts downstream commitment.
* **Timeout Behavior**: If an approval gate remains suspended past a configurable timeout window ($T_{\text{timeout}} = 300\text{ s}$), the decision defaults to a pre-registered fail-safe policy: reject hazardous price cuts, maintain current stock levels, and flag for supervisor escalation.

### 5.3 HITL Evaluation Metrics
1. **Approval Rate (%)**:
   $$\text{Approval Rate} = \frac{N_{\text{approved}}}{N_{\text{total decisions}}} \times 100\%$$
2. **Override Rate (%)**:
   $$\text{Override Rate} = \frac{N_{\text{overridden}}}{N_{\text{total decisions}}} \times 100\%$$
3. **Approval Latency / Time-to-Decision ($t_{\text{decision}}$)**:
   Elapsed time in seconds between gate suspension and operator resolution.
4. **Escalation Count**: Total count of decisions automatically flagged as high-risk and routed to supervisor review.
5. **Constraint / Policy Violations Prevented**: Count of proposed actions exceeding budget or margin constraints that were successfully blocked or corrected by the gate.

---

## 6. Execution Order (Steps 4 through 12)

The execution sequence is strictly frozen:

```
Step 4  ──> Forecasting / Model Replacement Definition & Design
Step 5  ──> Replacement Service Implementation & Interface Verification
Step 6  ──> Replacement Empirical Evaluation (Accuracy vs. Modularity)
Step 7  ──> M5 Operational Simulation Environment Setup & Data Pipeline
Step 8  ──> RetailOps Operational Simulation Evaluation (M5 Scenarios)
Step 9  ──> Selection & Detailed Specification of Reproducible Paper Architectures
Step 10 ──> Implementation & Execution of Same-Repository Architecture Comparison
Step 11 ──> Implementation & Execution of Human-in-the-Loop (HITL) Comparison
Step 12 ──> Results Consolidation, Synthesis, and Final Evaluation Reporting
```

---

## 7. Anti-Bias & Experimental Integrity Rules

To prevent post-hoc rationalization, selective cherry-picking, or data leakage, the following rules are permanently binding:

1. **No Scenario Alteration**: Operational disturbance parameters and scenarios (SCEN-01 through SCEN-05) are frozen. No scenario may be altered, added, or removed after inspecting execution outputs.
2. **No Selective Metric Reporting**: All metrics declared in Section 2, 3, 4, and 5 must be reported in full. Poorly performing metrics cannot be omitted or suppressed.
3. **No Selective Horizon Truncation**: Evaluation horizons ($H=30$ days for prototype; $H=28$ days for M5) cannot be shortened or shifted after running evaluations.
4. **No Test-Set Tuning**: Hyperparameters for forecasting models and replenishment policies must be tuned strictly on training splits. Iterative tuning against the test evaluation window is strictly prohibited.
5. **Honest Reporting of External Reproductions**: If an external paper architecture cannot be fully implemented due to missing documentation, missing source code, or missing weights, this limitation must be reported explicitly as a reproduction gap rather than claiming empirical equivalence or claiming system failure.

---

## 8. Acceptance and Success Criteria

| Experiment | Success Criteria |
| :--- | :--- |
| **Model Replacement** | 1. Zero modifications to existing sibling service files (0 LOC).<br>2. Configuration-only orchestration update ($\le 1$ LOC).<br>3. 100% downstream decision consumption rate without schema errors.<br>4. Unambiguous reporting of both MAE/RMSE and LOC churn without conflation. |
| **M5 Simulation** | 1. End-to-end execution across all 28 evaluation days.<br>2. Full reporting of Stockout Rate, Service Level, Holding Cost, and Reorder Cost.<br>3. Successful operational stress differentiation across SCEN-01 to SCEN-05. |
| **Architecture Comparison** | 1. All selected architectures execute against identical data and scenarios under `RANDOM_SEED = 42`.<br>2. Clear documentation of reproduced components vs. non-reproducible literature gaps.<br>3. Objective systems metrics reported without claims of commercial superiority. |
| **Human-in-the-Loop** | 1. Explicit verification of state suspension and resumption in Mode B.<br>2. Reliable capture of Approval Rate, Override Rate, and Time-to-Decision.<br>3. Demonstration of policy violation prevention under compound stress scenarios (SCEN-03 and SCEN-05). |

---

## 9. Methodological Limitations

1. **Synthetic vs. Real-World Distortion**: Synthetic local datasets provide deterministic control but lack the noisy demand correlations of multi-store retail supply networks.
2. **Subprocess Spawning Profile**: Host OS execution on Windows carries higher process-spawning latency than Unix fork mechanisms; absolute timing must be interpreted in light of local operating system characteristics.
3. **Literature Reproduction Fidelity**: Re-implementations of external architectures are constructed based on published algorithmic descriptions and interfaces, representing the architectural patterns rather than identical proprietary enterprise deployments.
