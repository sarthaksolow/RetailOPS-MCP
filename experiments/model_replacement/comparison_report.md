# Comparative Evaluation Report: Baseline SMA vs. Holt-Winters Replacement

**Document ID**: `REPORT-FORECASTING-COMPARISON-V1`  
**Date**: October 3, 2026  
**Status**: COMPLETE (Comparative Empirical Evaluation)  
**Evaluation Protocol**: [`PROTOCOL-EXP-FROZEN-V1`](file:///E:/Repositories/RetailOPS-MCP/experiments/evaluation_protocol.md)  
**Machine-Readable Data**: [`comparison_results.json`](file:///E:/Repositories/RetailOPS-MCP/experiments/model_replacement/comparison_results.json)  
**Baseline Report**: [`baseline.md`](file:///E:/Repositories/RetailOPS-MCP/experiments/model_replacement/baseline.md)  
**Replacement Implementation**: [`replacement_implementation.md`](file:///E:/Repositories/RetailOPS-MCP/experiments/model_replacement/replacement_implementation.md)

---

## 1. Executive Summary & Experimental Purpose

This report documents the frozen comparative evaluation between the existing 30-day Simple Moving Average (SMA) baseline and the newly implemented Holt-Winters Triple Exponential Smoothing replacement model. 

The evaluation was conducted strictly in accordance with [`PROTOCOL-EXP-FROZEN-V1`](file:///E:/Repositories/RetailOPS-MCP/experiments/evaluation_protocol.md) using identical datasets, identical train/test boundaries, an identical 30-day evaluation horizon ($H=30$), and identical error formulas without test-set tuning.

### Core Scientific Findings
1. **Algorithmic Accuracy**:
   - The 30-day Simple Moving Average baseline achieved a lower overall error across the test set (Mean MAE: **5.8410**, Mean RMSE: **7.1203**, Mean MAPE: **11.33%**).
   - The Holt-Winters additive model exhibited higher error (Mean MAE: **6.9138**, Mean RMSE: **7.8944**, Mean MAPE: **14.02%**), representing an increase of $+1.0729$ in MAE ($+18.37\%$), $+0.7741$ in RMSE ($+10.87\%$), and $+2.69\%$ in MAPE ($+23.71\%$).
   - This difference occurred consistently across all 7 categories because the underlying synthetic series contains tri-modal step cycles (e.g. $[8, 12, 10]$) with zero long-term trend, for which a flat trailing average provides a tighter central-tendency approximation than an additive trend-seasonal model with conservative smoothing parameters ($\alpha=0.25, \beta=0.05, \gamma=0.20$).
2. **Architectural Modularity**:
   - Replacing the forecasting implementation required **0 modifications** to existing service files and **0 modifications** to existing service lines of code.
   - The orchestrator required **0 lines of code changed**, resolving the replacement entirely through the existing runtime configuration variable (`RETAILOPS_FORECASTING_SERVER_PATH`).
   - The FastMCP tool interface contract (`getForecast`) achieved **100% schema compatibility**, and downstream replenishment and pricing services executed successfully with zero integration regressions.

---

## 2. Evaluation Methodology & Reproducibility Parameters

* **Dataset Path**: `servers/forecasting/data/sales_history.csv`
* **Evaluated Categories (7)**: `tv`, `laptop`, `phone`, `kitchen_appliances`, `fashion`, `groceries`, `electronics`
* **Total Series Records**: 854 daily observations (122 records per series spanning 2024-09-01 to 2024-12-31)
* **Training Partition**: First 92 observations per series (2024-09-01 to 2024-12-01). Used strictly for model fitting and moving average calculation.
* **Test Partition ($H=30$)**: Final 30 observations per series (2024-12-02 to 2024-12-31). Out-of-sample ground truth ($210$ total evaluation points).
* **Model Configurations**:
  - *Baseline*: 30-day SMA computed over training days 63 to 92.
  - *Holt-Winters Replacement*: Additive seasonal model with period $m = 7$, $\alpha = 0.25$, $\beta = 0.05$, $\gamma = 0.20$.
* **Execution Environment**: Windows 11 Enterprise (Build 26100), Python 3.12.0, x86_64 architecture.
* **Deterministic Seed**: Fixed random seed (`RANDOM_SEED = 42`). No stochastic sampling or external API dependencies utilized.

---

## 3. Quantitative Comparative Results

### 3.1 Aggregate Performance Across All Categories

| Metric Dimension | Baseline 30-day SMA | Holt-Winters Replacement | Absolute Difference | Relative Change (%) | Metric Trend |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **MAE (Primary)** | **5.8410** | **6.9138** | **+1.0729** | **+18.37%** | Worsened |
| **RMSE (Secondary)** | **7.1203** | **7.8944** | **+0.7741** | **+10.87%** | Worsened |
| **MAPE (Secondary)** | **11.33%** | **14.02%** | **+2.69%** | **+23.71%** | Worsened |
| **Evaluation Runtime** | < 5 ms | 10.18 ms | +5.74 ms | — | Fast / Deterministic |

### 3.2 Per-Category Performance Breakdown

All metrics below represent out-of-sample evaluations against the 30-day test set ($N=30$ per category):

| Category | Actual Test Mean | Base SMA MAE | HW Replacement MAE | MAE Difference | Base SMA RMSE | HW Replacement RMSE | Base SMA MAPE | HW Replacement MAPE | Category Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TV** | 10.00 | **1.33** | 1.58 | +0.24 (+18.37%) | **1.63** | 1.81 | **13.89%** | 17.15% | Baseline Closer |
| **Laptop** | 6.33 | **1.11** | 1.32 | +0.21 (+18.49%) | **1.25** | 1.41 | **17.66%** | 22.50% | Baseline Closer |
| **Phone** | 17.33 | **1.78** | 2.11 | +0.34 (+18.91%) | **2.05** | 2.30 | **10.27%** | 12.70% | Baseline Closer |
| **Kitchen Appliances** | 35.00 | **3.33** | 3.94 | +0.61 (+18.37%) | **4.08** | 4.52 | **9.72%** | 11.88% | Baseline Closer |
| **Fashion** | 60.00 | **6.67** | 7.89 | +1.22 (+18.37%) | **8.16** | 9.04 | **11.43%** | 14.03% | Baseline Closer |
| **Groceries** | 225.00 | **16.67** | 19.72 | +3.05 (+18.33%) | **20.41** | 22.61 | **7.50%** | 9.10% | Baseline Closer |
| **Electronics** | 115.00 | **10.00** | 11.83 | +1.83 (+18.33%) | **12.25** | 13.56 | **8.85%** | 10.78% | Baseline Closer |

---

## 4. Systems Modularity and Integration Effort

A primary objective of this experiment was to evaluate whether the forecasting engine could be replaced behind the Model Context Protocol boundary without cascading changes across the system.

### 4.1 Modularity Measurements

| Metric | Measured Value | Target / Reference | Evaluation Status |
| :--- | :--- | :--- | :--- |
| **Existing Service Files Modified** | **0 files** | 0 files | Verified (`catalog-enricher`, `replenishment`, `pricing-strategy` untouched) |
| **Existing Service LOC Modified** | **0 LOC** | 0 LOC | Verified |
| **Existing Orchestrator Files Modified** | **0 files** | $\le 1$ file | Verified (`client/orchestrator.py` untouched) |
| **Orchestration LOC Changed** | **0 LOC** | $\le 1$ LOC | Verified (Controlled via env var `RETAILOPS_FORECASTING_SERVER_PATH`) |
| **New Replacement Service LOC** | **241 LOC** | — | Verified (`servers/forecasting-statistical/server.py`) |
| **New Test Suite LOC** | **106 LOC** | — | Verified (`test_statistical_replacement.py`) |
| **Cross-Service Import Dependencies** | **0** | 0 | Verified (Decoupled over stdio JSON-RPC) |

### 4.2 Separation of Concerns Analysis
* **Accuracy vs. Modularity**: The fact that the 30-day SMA achieved lower error on this synthetic dataset does not diminish the modularity outcome. Conversely, the successful zero-code-churn replacement does not prove that Holt-Winters is superior in retail prediction.
* **Blast Radius**: The blast radius of the algorithmic swap was strictly contained to the new server executable and the configuration pointer.

---

## 5. Contract Verification and Downstream Compatibility

The replacement implementation was tested end-to-end through the FastMCP protocol to verify downstream operational integrity:

1. **Tool Invocation**: `MCPServerManager.call_forecasting("electronics", 30)` successfully spawned the replacement process, negotiated the JSON-RPC session handshake, and invoked `getForecast`.
2. **Schema Adherence (100%)**: Output payload returned all required fields (`category`, `base_forecast`, `seasonal_multiplier`, `historical_surge_factor`, `final_forecast`, `event`, `narrative`, and `model_metadata`).
3. **Downstream Execution**:
   - `replenishment` node consumed the replacement forecast output without schema parsing errors, producing valid reorder quantities and timing decisions.
   - `pricing-strategy` node consumed the forecasted demand without error, calculating recommended retail pricing and strategy tags.
4. **Automated Regression Suite**:
   All 5 assertions in [`test_statistical_replacement.py`](file:///E:/Repositories/RetailOPS-MCP/test_statistical_replacement.py) passed, and full regression batteries across existing tests remained completely green (`29/29 passed in 7.06s`).

---

## 6. Interpretation and Discussion

### What This Experiment Demonstrates
1. **Architectural Decoupling**: An operational microservice within an enterprise decision chain can be substituted with an alternative mathematical model with zero code modifications to upstream or downstream nodes, provided the FastMCP JSON-RPC interface contract is preserved.
2. **Protocol Independence from Model Performance**: Protocol stability and service boundaries operate independently of statistical model accuracy.
3. **Synthetic Dataset Structure**: In perfectly repeating cyclic synthetic series without trend, simpler estimators (such as fixed trailing moving averages) can outperform parameterized dynamic smoothing models because the true underlying data-generating process lacks trend or seasonal drift.

### What This Experiment Does NOT Demonstrate
1. It does **not** prove that Holt-Winters is universally inferior to moving averages; in complex non-stationary retail time series (such as Walmart M5), dynamic seasonal models typically outperform static moving averages.
2. It does **not** prove that RetailOps achieves higher commercial retail profit than monolithic architectures.
3. It does **not** prove that every arbitrary machine learning model can be integrated with zero configuration; models requiring specialized GPU dependencies or continuous retraining pipelines would introduce operational deployment considerations outside this stdio experiment scope.

---

## 7. Methodological Limitations

1. **Synthetic Data Homogeneity**: The 7 product categories share similar synthetic tri-modal demand patterns, causing relative model performance to be uniform across all categories.
2. **Pre-Set Smoothing Parameters**: Parameters ($\alpha=0.25, \beta=0.05, \gamma=0.20$) were pre-registered in the implementation protocol without tuning against the test set. While adhering to strict anti-bias rules, this prevented optimal parameter convergence for this specific dataset.
3. **Windows Subprocess Spawning**: Executing the server as an independent OS subprocess introduces lifecycle overhead, which was amortized in persistent session evaluations but remains relevant during cold-start process-per-call operations.
