# RetailOps Baseline Forecasting Evaluation Report

**Document ID**: `REPORT-BASELINE-FORECASTING-V1`  
**Date**: October 3, 2026  
**Status**: COMPLETE (Baseline established for Model Replacement Evaluation)  
**Evaluation Protocol**: [`PROTOCOL-EXP-FROZEN-V1`](file:///E:/Repositories/RetailOPS-MCP/experiments/evaluation_protocol.md)  
**Machine-Readable Results**: [`baseline_results.json`](file:///E:/Repositories/RetailOPS-MCP/experiments/model_replacement/baseline_results.json)

---

## 1. Executive Summary

This report establishes the baseline evaluation for the model replacement experiment. The objective is to evaluate the existing production forecasting implementation against a standardized out-of-sample test split, recording primary and secondary accuracy metrics alongside FastMCP schema adherence.

In accordance with the frozen evaluation protocol:
- **No LLM or network dependency** was used for generating numerical values.
- **No replacement model** (such as ARIMA, Prophet, or LightGBM) was implemented.
- **Zero code modifications** were made to existing production services.
- The evaluation was conducted strictly across the frozen historical dataset with an out-of-sample test horizon of $H = 30$ days.

---

## 2. Baseline Forecasting Method Breakdown

The baseline implementation in `servers/forecasting/server.py` derives its predictions via a three-component pipeline:

1. **Base Forecast (`base_forecast`)**:
   Calculated by taking the arithmetic mean of daily sales over the trailing 30 days of the historical series:
   $$\text{base\_forecast} = \frac{1}{30}\sum_{t=N-29}^N y_t$$
2. **Seasonal Multiplier (`seasonal_multiplier`)**:
   Determined by querying `events.json` for upcoming retail events within a 180-day lookahead window from the evaluation reference point. For December evaluations, Christmas carries a seasonal multiplier of $1.30$.
3. **Historical Surge Factor (`historical_surge_factor`)**:
   Queried from `surge_profile.json` for the specific category and upcoming event (e.g. $1.60$ for TV during Christmas).
4. **Final Forecast (`final_forecast`)**:
   $$\text{final\_forecast} = \text{round}(\text{base\_forecast} \times \text{seasonal\_multiplier} \times \text{historical\_surge\_factor}, 2)$$
5. **Event (`event`)**:
   String identifier of the active calendar event (or `None`).

---

## 3. Dataset Specification and Train / Test Partition

* **Dataset Path**: `servers/forecasting/data/sales_history.csv`
* **Auxiliary Data**: `servers/forecasting/data/events.json`, `servers/forecasting/data/surge_profile.json`
* **Evaluated Series Count**: 7 retail categories (`tv`, `laptop`, `phone`, `kitchen_appliances`, `fashion`, `groceries`, `electronics`)
* **Total Observations**: 854 records (122 daily observations per category spanning 2024-09-01 to 2024-12-31)
* **Training Partition**:
  - Date Range: 2024-09-01 to 2024-12-01 (92 daily observations per series)
  - Purpose: Calculation of the trailing 30-day baseline moving average strictly prior to the test boundary.
* **Test Partition (Evaluation Horizon $H = 30$)**:
  - Date Range: 2024-12-02 to 2024-12-31 (30 daily observations per series)
  - Purpose: Out-of-sample evaluation of forecast predictions against actual realized sales. No future data leakage permitted.

---

## 4. Quantitative Baseline Results

Accuracy was evaluated across all 7 retail categories for both the unadjusted 30-day Simple Moving Average (Base SMA) and the event-adjusted forecast.

### 4.1 Summary of Aggregate Metrics
* **Total Series Evaluated**: 7 categories
* **Evaluation Horizon**: $H = 30$ days per category ($210$ total evaluation points)
* **Primary Metric (MAE)**:
  - Base 30-day SMA: **5.8410**
  - Event-Adjusted Forecast: **42.3633**
* **Secondary Metric (RMSE)**:
  - Base 30-day SMA: **7.1203**
  - Event-Adjusted Forecast: **42.9804**
* **Secondary Metric (MAPE)**:
  - Base 30-day SMA: **11.33%**
  - Event-Adjusted Forecast: **85.52%**
* **Evaluation Execution Runtime**: **4.44 ms**

### 4.2 Per-Category Performance Breakdown

| Category | Train Samples | Test Samples | Base Daily SMA | Event-Adjusted Daily Rate | Base MAE (Primary) | Base RMSE | Base MAPE (%) | Adjusted MAE | Adjusted RMSE | Adjusted MAPE (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TV** | 92 | 30 | 10.00 | 20.80 | **1.33** | 1.63 | 13.89% | 10.80 | 10.92 | 113.78% |
| **Laptop** | 92 | 30 | 6.33 | 11.52 | **1.11** | 1.25 | 17.66% | 5.19 | 5.33 | 88.80% |
| **Phone** | 92 | 30 | 17.33 | 31.54 | **1.78** | 2.05 | 10.27% | 14.21 | 14.35 | 84.50% |
| **Kitchen Appliances** | 92 | 30 | 35.00 | 68.25 | **3.33** | 4.08 | 9.72% | 33.25 | 33.50 | 97.71% |
| **Fashion** | 92 | 30 | 60.00 | 117.00 | **6.67** | 8.16 | 11.43% | 57.00 | 57.58 | 98.71% |
| **Groceries** | 92 | 30 | 225.00 | 321.75 | **16.67** | 20.41 | 7.50% | 96.75 | 98.88 | 44.19% |
| **Electronics** | 92 | 30 | 115.00 | 194.35 | **10.00** | 12.25 | 8.85% | 79.35 | 80.29 | 70.95% |
| **Average** | **92** | **30** | — | — | **5.84** | **7.12** | **11.33%** | **42.36** | **42.98** | **85.52%** |

---

## 5. Interface Contract Verification

The baseline evaluation verified 100% compliance with the FastMCP tool contract defined in `servers/forecasting/schema.json` and the frozen protocol:

* **Tool Name**: `getForecast`
* **Schema Conformance**:
  - `category` (string): Present across all outputs
  - `base_forecast` (number): Non-negative float
  - `seasonal_multiplier` (number): Value $\ge 1.0$
  - `historical_surge_factor` (number): Value $\ge 1.0$
  - `final_forecast` (number): Non-negative float
  - `event` (string or null): Properly mapped
  - `narrative` (string): Deterministic explanation string generated without external API dependencies
* **Downstream Compatibility**: Verified schema parity matches the inputs expected by `client/orchestrator.py` (`call_replenishment` and `call_pricing`).

---

## 6. Code Changes Audit

* **Files Modified**: `0`
* **Files Added**: 
  - `experiments/model_replacement/baseline_results.json` (Machine-readable empirical metrics)
  - `experiments/model_replacement/baseline.md` (Formal evaluation documentation)
* **Production Code Alterations**: None. The deterministic offline evaluation path was executed using standard Python scientific tooling (`pandas`, `numpy`) directly referencing the existing raw datasets without altering server implementations or test suites.

---

## 7. Methodological Limitations & Observations

1. **Synthetic Data Characteristics**:
   The baseline dataset represents a 4-month synthetic retail profile with regular cyclic demand patterns. The base 30-day SMA tracks historical steady-state sales closely (Mean MAPE: $11.33\%$).
2. **Event Multiplier Surge Dynamics**:
   The existing heuristic applies the full event surge ($1.30\text{x} \times \text{surge}$) across the entire 30-day window rather than localizing it to specific event days. In real historical December data, sales remain near baseline until immediately before the holiday, resulting in elevated MAE for the simple multiplied rate. This provides a clear, measurable empirical baseline against which advanced statistical models can be evaluated in Step 6.
3. **Pure Separation of Concerns**:
   These metrics represent domain forecasting accuracy only. They do not indicate architectural modularity, process boundary overhead, or orchestration robustness.
