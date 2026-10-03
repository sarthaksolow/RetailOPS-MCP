# Methodological & Experimental Limitations

This document provides a comprehensive, transparent inventory of the methodological, experimental, and empirical limitations governing the RetailOps research evaluation.

To preserve scientific rigor, these boundaries must be explicitly reported in any publication or analysis based on these artifacts.

---

## 1. Dataset & Scope Limitations

### 1.1 Limited Number of Store-Item Series
- The operational M5 evaluation was conducted on **five store-item series** from California store 1 (`CA_1_FOODS_1_004`, `CA_1_FOODS_1_012`, `CA_1_HOUSEHOLD_1_007`, `CA_1_HOBBIES_1_004`, `CA_1_HOBBIES_1_008`).
- While these series were selected to represent different product categories, price points, and demand velocities, they represent a small fraction of the 30,490 series available in the full M5 dataset.
- Findings cannot be assumed to generalize across the entire retail catalog, highly seasonal items, or slow-moving / highly intermittent demand profiles.

### 1.2 Finite 28-Day Operational Horizon
- The discrete-event inventory simulation was evaluated over a **fixed 28-day window** ($H=28$, days `d_1914` to `d_1941`).
- A 28-day horizon introduces artificial boundary conditions near the end of the simulation. Specifically, replenishment orders placed late in the horizon (e.g., day 22+ under a 7-day lead time, or day 8+ under a 21-day lead time) cannot arrive before evaluation concludes.
- While the human-supervised mode mitigated this through horizon filtering, infinite-horizon rolling operations would absorb late-arriving inventory into subsequent sales cycles.

### 1.3 Selected Predefined Scenarios
- Operational evaluation relied on **five predefined stress scenarios** (`SCEN-01` to `SCEN-05`), manipulating demand multipliers, initial stock levels, lead times, and supplier reliability.
- Real-world retail supply chains experience continuous, correlated, and compound disruptions (e.g., simultaneous price elasticity shifts, port congestion, multi-echelon warehouse constraints) that were not modeled in these discrete scenarios.

---

## 2. Simulation Mechanics & Operational Assumptions

### 2.1 Lost-Sales Formulation vs Backlogging
- The inventory simulator implements an unbacklogged **lost-sales formulation**: unsatisfied daily demand is permanently lost and does not accumulate as backorders.
- In many retail and wholesale environments, unsatisfied customer orders may be partially backlogged, substituted with alternative items, or fulfilled from secondary distribution centers.

### 2.2 Deterministic & Simplified Supplier Model
- While supplier reliability was modeled probabilistically in stress scenarios (e.g., 0.70 delivery probability), actual supplier lead times followed deterministic scenario specifications ($L=7$ or $L=21$ days) rather than continuous stochastic distributions (such as log-normal or Weibull lead-time distributions).
- The supplier model assumes infinite supplier production capacity subject only to Minimum Order Quantity (MOQ) and Maximum Order Quantity (MaxOQ), ignoring supplier stockouts, batch allocations, or tiered volume pricing.

### 2.3 Single-Echelon Store Simulation
- The simulator models a **single-echelon retail store** receiving goods directly from external suppliers.
- Modern enterprise retail networks operate multi-echelon architectures comprising central distribution centers (CDCs), regional fulfillment hubs, cross-docking facilities, and store networks. Inter-echelon lead times and lateral store transfers were not evaluated.

---

## 3. External Architecture Comparison Boundaries

### 3.1 Bounded Pattern Reproductions
- The comparisons with **Flowr**, **WorkflowLLM**, and **Agentic Replenishment** represent **bounded reproductions of published architectural patterns** rather than complete implementations of the original proprietary systems.
- Each architecture was implemented from its published literature description, sharing the common `BaseDecisionProvider` contract and operating under identical simulation inputs:
  - *Flowr*: Centralized reasoning coordinator pattern with modular tool functions.
  - *WorkflowLLM*: Generative plan-then-execute pattern with dynamic parameter binding.
  - *Agentic Replenishment*: Single-domain autonomous direct replenishment agent pattern.

### 3.2 Absence of Original Checkpoints, Training Sets, and Fine-Tuning
- The evaluations did not utilize the original proprietary model checkpoints, domain-specific prompt collections, or private enterprise fine-tuning datasets utilized in the referenced publications.
- Performance outcomes measure the structural behavior of the architectural coordination pattern within the frozen M5 simulation, not the proprietary capability of the original commercial platforms.

---

## 4. Forecasting Model Scope & Findings

### 4.1 Statistical Scope
- The statistical replacement experiment evaluated a **Holt-Winters additive exponential smoothing model** against a **30-day Simple Moving Average (SMA)** baseline across 7 product categories over a 30-day forecast horizon.
- The evaluation did not include modern deep learning architectures (e.g., Temporal Fusion Transformers, PatchTST, DeepAR) or foundation time-series models (e.g., Chronos, TimesFM).

### 4.2 Decoupling of Modularity from Predictive Accuracy
- The Holt-Winters model exhibited higher error metrics (MAE 6.9138 vs 5.8410; MAPE 14.02% vs 11.33%) than the baseline SMA on the evaluated historical sales dataset.
- This outcome is reported as an empirical finding: MCP provides contract-preserving modularity and process isolation, but architectural modularity does not confer algorithmic predictive accuracy.

---

## 5. Human-in-the-Loop (HITL) Supervisory Limitations

### 5.1 Simulated Operator Policy vs Human Subjects
- The human supervisor in Step 11 was implemented as a **deterministic, rule-based simulated operator policy** adhering strictly to `PROTOCOL-EXP-FROZEN-V1` Section 5.2.
- The experiment was deliberately designed to eliminate subjective human variance and enable bit-for-bit reproducibility; it does **not** constitute human-subject testing or an empirical study of human decision-makers.

### 5.2 Programmatic Definition of "Prevented Policy Violations"
- The recorded 153 "prevented policy violations" represent instances where proposed orders breached programmatic governance constraints (budget cap of $100.00, or late arrival past horizon $t + L > 28$) within the simulated operator policy.
- These metrics do not reflect real-world human oversight, human error correction, or organizational compliance monitoring.

### 5.3 Static Deliberation Latency
- Supervisory deliberation latency was modeled as a constant 15.0 seconds per escalated decision.
- Real-world human operator response times vary significantly based on user interface ergonomics, alert volume, operational fatigue, cognitive load, and organizational shift schedules.

---

## 6. Enterprise & Deployment Scope

### 6.1 Lack of Live Production Deployment
- RetailOps has been evaluated exclusively in offline simulation environments, synthetic benchmarks, and historical dataset replays.
- The framework has not been deployed in live retail production environments, nor has it processed live customer transactions or physical warehouse inventory movements.

### 6.2 Statistical Significance Analysis Scope
- Across the deterministic M5 simulation runs (where demand traces and starting states were fixed per scenario), outcomes are exact and bit-for-bit reproducible under random seed 42.
- Because the evaluation focused on deterministic policy comparisons across fixed scenarios rather than randomized cross-sectional sampling across thousands of stores, formal hypothesis testing (such as paired t-tests or ANOVA) was not conducted across broader populations.

---

## 7. Summary Statement on Generalization

The empirical findings documented in this repository provide concrete evidence regarding:
1. Architectural modularity, process isolation, and contract preservation under the Model Context Protocol.
2. Comparative operational dynamics between multi-agent reasoning, continuous review policies, and alternative coordination patterns within a standardized discrete-event simulator.
3. The structural mechanics of supervisory approval gates in moderating operating expenditure.

These findings do not establish universal optimality, production readiness, or predictive superiority across general retail supply chain operations.
