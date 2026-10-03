# M5 Operational Simulation Environment Design Specification

**Document ID**: `DESIGN-M5-SIMULATION-V1`  
**Date**: October 3, 2026  
**Status**: COMPLETE (Simulation Infrastructure & Validation)  
**Evaluation Protocol**: [`PROTOCOL-EXP-FROZEN-V1`](file:///E:/Repositories/RetailOPS-MCP/experiments/evaluation_protocol.md)  
**Target Step**: Step 7 (Infrastructure only; operational comparisons deferred to Step 8)

---

## 1. Executive Summary & Purpose

This document establishes the architecture and design of the discrete-event inventory simulation environment for evaluating enterprise decision-orchestration frameworks under realistic retail demand.

The environment utilizes the official Walmart M5 Forecasting dataset, isolating a representative set of store-item time series from California store 1 (`CA_1`). The simulation accurately models:
- Daily inventory state transitions
- Customer demand fulfillment and lost-sales accounting
- Supplier procurement order placement, batching, and lead-time delays
- Delivery pipeline tracking and arrivals
- Holding costs, procurement costs, and inventory constraint enforcement

---

## 2. Dataset Acquisition, Validation, and Selected Series

### 2.1 Raw Dataset Audit & SHA-256 Hashes
The official M5 competition dataset was acquired from the validated Nixtla dataset repository (licensed for public research) and staged in `data/m5/raw/`. The raw CSV files were audited and verified with the following cryptographic signatures:

| Raw File Name | File Size (Bytes) | Cryptographic SHA-256 Hash |
| :--- | :--- | :--- |
| **`sales_train_evaluation.csv`** | 121,168,898 bytes | `c21a519596680feb86f27a9e62f6c8b583f8be60c2c195f080ae8ca2990af2b7` |
| **`calendar.csv`** | 112,477 bytes | `568d0fe5f41790142379698732908e4e57432c1c6396f3f59fb880a9c2b54231` |
| **`sell_prices.csv`** | 237,073,689 bytes | `5c7cf045b1abbdc8d5007809c40b3682c5216075937f93e2cef01caddc4a30d9` |

*Verification Rule*: Never substitute synthetic data while representing it as M5.

### 2.2 Granularity & Selected Store-Item Series
The evaluation operates at the **store-item daily level** within Walmart store `CA_1`. Five diverse products across the primary M5 categories (`FOODS`, `HOUSEHOLD`, `HOBBIES`) were selected based on consistent sales history and non-intermittent demand during the evaluation window:

| Series Identifier | Store ID | Item ID | Category | Department | Unit Sell Price ($) | Wholesale Unit Cost ($) | Daily Holding Cost Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`CA_1_FOODS_1_004`** | `CA_1` | `FOODS_1_004` | `FOODS` | `FOODS_1` | $1.96 | $1.18 | 0.001 (0.1%/day) |
| **`CA_1_FOODS_1_012`** | `CA_1` | `FOODS_1_012` | `FOODS` | `FOODS_1` | $5.64 | $3.38 | 0.001 (0.1%/day) |
| **`CA_1_HOUSEHOLD_1_007`** | `CA_1` | `HOUSEHOLD_1_007` | `HOUSEHOLD` | `HOUSEHOLD_1` | $1.48 | $0.89 | 0.001 (0.1%/day) |
| **`CA_1_HOBBIES_1_004`** | `CA_1` | `HOBBIES_1_004` | `HOBBIES` | `HOBBIES_1` | $4.64 | $2.78 | 0.001 (0.1%/day) |
| **`CA_1_HOBBIES_1_008`** | `CA_1` | `HOBBIES_1_008` | `HOBBIES` | `HOBBIES_1` | $0.48 | $0.29 | 0.001 (0.1%/day) |

### 2.3 Train / Test Partition Boundaries
* **Training Partition**: Days `d_1` to `d_1913` (2011-01-29 to 2016-04-24). Contains 1,913 days of historical sales utilized strictly for historical average demand calculation.
* **Evaluation Horizon ($H=28$ days)**: Days `d_1914` to `d_1941` (2016-04-25 to 2016-05-22). Out-of-sample ground truth customer demand.
* **Data Leakage Guarantee**: The decision provider context receives strictly training historical statistics and real-time state ($I_t, R_t$); it has zero access to future demand $d_{t+1 \dots H}$.

---

## 3. Inventory Simulator Mechanics & Event Timing

To eliminate ambiguity in metric accounting, daily simulation events occur in a strictly ordered sequence:

```
[Day t Begins]
      │
      ▼
1. MORNING (Receipts Arrival)
   Orders placed at day (t - L) arrive and are added to on-hand stock:
   available_inventory = starting_inventory + arrivals
      │
      ▼
2. MID-DAY (Customer Demand & Fulfillment)
   Realized customer demand d_t arrives.
   fulfilled_demand = min(available_inventory, d_t)
   lost_sales = max(0, d_t - available_inventory)
   ending_inventory = available_inventory - fulfilled_demand
      │
      ▼
3. AFTERNOON (Holding Cost & Stockout Assessment)
   Holding cost accrued on ending_inventory:
   daily_holding_cost = ending_inventory * unit_cost * holding_rate
   Stockout event flagged if lost_sales > 0 or ending_inventory == 0 under demand
      │
      ▼
4. EVENING (Decision Provider Review & Replenishment)
   Decision provider evaluates context and emits ReplenishmentDecision.
   If order_quantity > 0:
     Enforce Minimum/Maximum order constraints (log violation if broken).
     Pipeline order queued to arrive at day (t + L).
     Procurement expense accrued.
[Day t Ends]
```

### Operational Cost Equations
* **Daily Holding Cost ($C_{\text{hold}}$)**:
  $$C_{\text{hold}, t} = I_{\text{ending}, t} \times c_{\text{unit}} \times h_{\text{rate}}$$
* **Daily Procurement Cost ($C_{\text{order}}$)**:
  $$C_{\text{order}, t} = Q_t \times c_{\text{unit}} \times \text{cost\_index} + \mathbb{I}(Q_t > 0) \times S_{\text{order}}$$

---

## 4. Operational Scenarios Implementation

All five scenarios specified in [`PROTOCOL-EXP-FROZEN-V1`](file:///E:/Repositories/RetailOPS-MCP/experiments/evaluation_protocol.md) are codified with fixed random seed $42$:

| Scenario ID | Name | Initial Inventory Factor ($k_{\text{init}}$) | Demand Multiplier | Lead Time ($L$) | Supplier Reliability | MOQ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`SCEN-01`** | **Normal Demand** | $1.0\times$ ($\bar{d} \times L$) | $1.0\times$ | 7 days | 0.95 | 20 |
| **`SCEN-02`** | **Demand Spike** | $1.0\times$ | $2.5\times$ | 7 days | 0.95 | 20 |
| **`SCEN-03`** | **Low Inventory** | $0.2\times$ ($< 2$ days runway) | $1.0\times$ | 7 days | 0.95 | 20 |
| **`SCEN-04`** | **Supplier Delay** | $1.0\times$ | $1.0\times$ | 21 days (tripled) | 0.65 | 20 |
| **`SCEN-05`** | **Compound Stockout Risk** | $0.2\times$ | $2.5\times$ | 14 days (doubled) | 0.70 | 20 |

---

## 5. Common Decision Provider Interface

The simulator accepts decisions via the abstract contract `BaseDecisionProvider`:

```python
class BaseDecisionProvider(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str:
        pass

    @abstractmethod
    def decide(self, context: OperationalDecisionContext) -> ReplenishmentDecision:
        pass
```

### Reference Baseline Decision Provider
A standard $(s, S)$ continuous review inventory policy is provided in `FixedThresholdDecisionProvider`. It reorders when effective inventory ($I_{\text{on\_hand}} + I_{\text{in\_transit}}$) drops below reorder point $s = \bar{d} \cdot L + z \sigma_L$, targeting level $S = s + 7\bar{d}$ while enforcing minimum order quantity constraints.

---

## 6. Metric Definitions & Formulas

1. **Stockout Rate (%)**:
   $$\text{Stockout Rate} = \frac{\sum_{t=1}^{28} \mathbb{I}(I_t = 0 \land d_t > 0 \lor \text{lost\_sales}_t > 0)}{28} \times 100\%$$
2. **Service Level (%)**:
   $$\text{Service Level} = \frac{\sum_{t=1}^{28} \text{fulfilled}_t}{\sum_{t=1}^{28} d_t} \times 100\%$$
3. **Total Holding Cost ($)**: Cumulative sum of daily holding expenses over the 28-day window.
4. **Total Replenishment Cost ($)**: Cumulative sum of wholesale order expenses.
5. **Constraint Violations Count**: Total number of orders placed below MOQ ($20$ units) or above capacity ($500$ units).

---

## 7. Verification Results

Deterministic unit tests implemented in [`test_m5_simulator.py`](file:///E:/Repositories/RetailOPS-MCP/test_m5_simulator.py) passed all 6 test suites (`6/6 passed in 0.17s`):
- `test_01_inventory_conservation_and_lost_sales`: Verified exact physical conservation ($I_{\text{avail}} = I_{\text{start}} + R_t$, $I_{\text{end}} = I_{\text{avail}} - \text{fulfilled}$, $d_t = \text{fulfilled} + \text{lost}$).
- `test_02_order_arrival_timing`: Verified order placed at day $t$ with $L=7$ arrives at day $t+7$.
- `test_03_supplier_delay_impact`: Verified $L=21$ delays arrival to day $22$.
- `test_04_constraint_enforcement`: Verified ordering 10 units under $\text{MOQ}=20$ flags a constraint violation.
- `test_05_reproducibility`: Verified identical seeds produce bit-for-bit identical results across repeated runs.
- `test_06_metric_calculation_accuracy`: Verified exact mathematical agreement with manual calculation.

*Regression verification*: Full repository test suite passed (`35/35 passed in 7.82s`).

---

## 8. Remaining Limitations

1. **Deterministic Lead-Time Arrivals**: Lead times are currently evaluated as fixed intervals ($L=7, 14, 21$) rather than stochastic distributions.
2. **Uncoupled Multi-Echelon Dependencies**: Each store-item is simulated as an independent inventory stocking point without cross-store transshipment or central DC replenishment.
3. **Lost Sales vs Backorders**: Unfulfilled customer demand is modeled as lost sales rather than backordered demand, matching standard grocery and discount retail dynamics.
