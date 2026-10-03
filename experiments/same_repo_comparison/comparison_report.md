# Cross-Architecture Operational & Modularity Comparison Report: Bounded Pattern Reproductions

**Document ID**: `REPORT-SAME-REPO-COMPARISON-V1`  
**Evaluation Phase**: Step 10 — Same-Repository Architecture Comparison  
**Protocol Reference**: [`PROTOCOL-EXP-FROZEN-V1`](file:///E:/Repositories/RetailOPS-MCP/experiments/evaluation_protocol.md)  
**Machine-Readable Dataset**: [`results.json`](file:///E:/Repositories/RetailOPS-MCP/experiments/same_repo_comparison/results.json)  
**Date**: October 3, 2026  
**Status**: COMPLETE (Verified & Audited)

> [!IMPORTANT]
> **Explicit Scope Boundary — Bounded Pattern Reproductions**:  
> The external systems evaluated in this investigation (`flowr_coordinator`, `workflowllm_generative`, `agentic_replenishment`) are **bounded algorithmic reproductions of published architectural orchestration patterns**. They are **not** implementations of the original authors' proprietary model checkpoints, private fine-tuned weights (e.g., Flowr's specialist LLM consortium, WorkflowLlama), closed commercial datasets (e.g., WorkflowBench), or enterprise ERP connectors. These reproductions evaluate how the structural decision and orchestration topologies behave when placed under identical retail operational conditions.

---

## 1. Executive Summary & Research Question

This investigation addresses the empirical question:
> *"How do distinct enterprise decision-orchestration architectures behave when placed under identical retail operational simulation conditions?"*

To isolate the operational effects of architectural topologies, four distinct systems were evaluated under the standardized M5 discrete-event inventory simulation environment established in Step 7:
1. **RetailOps MCP (`retailops_mcp`)**: Multi-process FastMCP microservices orchestrated by a compiled LangGraph `StateGraph` Directed Acyclic Graph (DAG) with proportional lead-time safety buffering.
2. **Flowr Coordinator Pattern (`flowr_coordinator`)**: Bounded reproduction of the centralized reasoning coordinator pattern dispatching queries dynamically to modular domain tool functions (Bandara et al., 2026).
3. **WorkflowLLM Generative Pattern (`workflowllm_generative`)**: Bounded reproduction of the two-phase generative orchestration pattern: explicit step-by-step workflow plan synthesis followed by dynamic parameter binding and execution (Fan et al., ICLR 2025).
4. **Agentic Inventory Replenishment Pattern (`agentic_replenishment`)**: Bounded reproduction of the direct-control single-domain autonomous agent loop coupling inventory perception directly to supplier orders (Syed et al., ICBDT 2025).
5. **Fixed-Threshold Benchmark (`fixed_threshold_baseline`)**: Standard continuous review $(s, S)$ mathematical heuristic included as an uncoordinated reference baseline.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        CROSS-ARCHITECTURE SUMMARY OVERVIEW                             │
├─────────────────────────┬──────────────┬─────────────┬─────────────┬─────────────┬─────┤
│ Architecture Approach   │ Stockout (%) │ Service (%) │ Mean Cost $ │ Lost Units  │ LOC │
├─────────────────────────┼──────────────┼─────────────┼─────────────┼─────────────┼─────┤
│ RetailOps MCP           │ 21.43%       │ 75.81%      │ $245.89     │ 1,591       │ 94* │
│ Flowr Coordinator       │ 25.57%       │ 71.63%      │ $194.29     │ 1,920       │ 150 │
│ WorkflowLLM Generative  │ 25.43%       │ 72.25%      │ $196.51     │ 1,870       │ 217 │
│ Agentic Replenishment   │ 24.86%       │ 72.58%      │ $200.52     │ 1,811       │ 76  │
│ Fixed-Threshold Base    │ 26.29%       │ 70.68%      │ $199.50     │ 1,939       │ 53  │
└─────────────────────────┴──────────────┴─────────────┴─────────────┴─────────────┴─────┘
*Note: RetailOps LOC reflects the evaluation adapter connecting to existing microservices.
```

### Critical Disclaimers & Non-Equivalence Boundaries
* **Absence of Hierarchy Framing**: In accordance with the experimental protocol, architectures are evaluated without hierarchy or rank ordering. Each approach exhibited distinct operational trade-offs across the disturbance scenarios. RetailOps recorded 21.43% stockout rate, 75.81% service level, and an operating cost of $245.89. The Flowr coordinator pattern recorded 25.57% stockout rate, 71.63% service level, and an operating cost of $194.29. The WorkflowLLM generative pattern recorded 25.43% stockout rate, 72.25% service level, and $196.51 operating cost. The Agentic Replenishment pattern recorded 24.86% stockout rate, 72.58% service level, and $200.52 operating cost.
* **Separation of Policy vs Architecture**: Operational outcomes reflect the mathematical interaction between safety buffer sizing, reorder thresholds, and review timing. MCP and LangGraph provide modular service encapsulation and structured communication; they do not dictate the mathematical formulas for target stock.
* **Strict Bounded Reproductions**: External systems are bounded reproductions of published architectural patterns, not complete implementations of original commercial infrastructure, proprietary LLM weights, or enterprise ERP databases.

---

## 2. Architecture Descriptions & Structural Topologies

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                         STRUCTURAL ORCHESTRATION TOPOLOGIES                              │
├──────────────────────────┬──────────────────────────┬────────────────────────────────────┤
│ System Identifier        │ Topology Classification  │ Structural Dispatch Mechanism      │
├──────────────────────────┼──────────────────────────┼────────────────────────────────────┤
│ retailops_mcp            │ Compiled Linear DAG      │ Static LangGraph StateGraph        │
│ flowr_coordinator        │ Centralized Star         │ Dynamic coordinator query routing  │
│ workflowllm_generative   │ Plan-then-Execute        │ Generative planning & binding graph│
│ agentic_replenishment    │ Monolithic Loop          │ Direct perception-action agent     │
│ fixed_threshold_baseline │ Static Formula           │ Deterministic (s, S) threshold     │
└──────────────────────────┴──────────────────────────┴────────────────────────────────────┘
```

### 2.1 RetailOps MCP Framework (`retailops_mcp`)
* **Source**: RetailOps Local Framework.
* **Topology**: Compiled Directed Acyclic Graph (DAG) using LangGraph `StateGraph`.
* **Mechanism**: State progresses through a fixed sequence of nodes (`demand_risk` $\rightarrow$ `festival` $\rightarrow$ `inventory` $\rightarrow$ `safety` $\rightarrow$ `reorder` $\rightarrow$ `timing`). Inter-service communication is encapsulated via FastMCP servers communicating over standard input/output (STDIO) JSON-RPC 2.0 with persistent session pooling.
* **Safety Buffering**: Proportional safety buffer ($1.25 \times \bar{d} \times L$), multiplied by $1.2\times$ during promotional events.

### 2.2 Bounded Pattern Reproduction: Flowr Coordinator (`flowr_coordinator`)
* **Source Reference**: Bandara et al. (April 2026), arXiv:2604.05987.
* **Topology**: Centralized reasoning coordinator in a dynamic star topology.
* **Mechanism**: A central coordinator receives the state context and queries modular domain tools:
  1. `monitor_inventory`: Assesses runway and classifies risk.
  2. If risk is elevated, dispatches `forecast_demand`, `plan_procurement`, and `coordinate_supplier`.
  3. If risk is low, terminates evaluation early, deferring procurement calls.
* **Safety Buffering**: Coordinator balancing buffer ($1.8 \times \bar{d} \times \sqrt{L}$).

### 2.3 Bounded Pattern Reproduction: WorkflowLLM Generative (`workflowllm_generative`)
* **Source Reference**: Fan et al. (ICLR 2025), arXiv:2411.02052.
* **Topology**: Dynamic two-phase plan-then-execute engine.
* **Mechanism**:
  - *Phase 1 (Plan Synthesis)*: Synthesizes an explicit execution plan with discrete steps (`audit_effective_inventory`, `evaluate_disturbance_context`, `synthesize_target_inventory`, `bind_supplier_constraints`, `classify_timing_and_risk`).
  - *Phase 2 (Plan Execution)*: Executes steps sequentially, dynamically binding outputs of earlier steps as inputs to downstream operations.
* **Safety Buffering**: Disturbance-adaptive buffer scaling based on scenario intent ($1.5 \times$ to $2.0 \times \bar{d} \times \sqrt{L}$).

### 2.4 Bounded Pattern Reproduction: Agentic Inventory Replenishment (`agentic_replenishment`)
* **Source Reference**: Syed et al. (ICBDT 2025), arXiv:2511.23366.
* **Topology**: Direct single-domain autonomous agent loop.
* **Mechanism**: Unbundled single-node control loop. Directly consumes on-hand stock, pipeline in-transit orders, and daily demand rate, immediately applying economic reorder point logic ($ROP = \bar{d} L + 1.65 \bar{d} \sqrt{L}$) and enforcing supplier batching without multi-service pipeline overhead.
* **Safety Buffering**: Heuristic safety stock ($1.65 \times \bar{d} \times \sqrt{L} \times \text{event\_factor}$).

---

## 3. Explicit Reproduction Boundaries & Excluded Proprietary Assets

To maintain scientific integrity, the boundaries between the original publications and the reproduced patterns are explicitly defined:

| Architecture | Reproduced Architectural Pattern | Excluded Non-Reproducible Components |
| :--- | :--- | :--- |
| **Flowr** | Centralized reasoning coordinator; dynamic modular tool query routing; early deferral logic. | Proprietary commercial fine-tuned specialist LLM weights; multi-echelon regional distribution center logistics. |
| **WorkflowLLM** | Two-phase generative plan synthesis; dynamic parameter binding across sequential operations. | The 106,763-sample WorkflowBench dataset; full WorkflowLlama model training checkpoints; open-domain web APIs. |
| **Agentic Replenishment** | Direct perception-action replenishment loop; unified supplier constraint enforcement. | Enterprise ERP database connectors; online continuous reinforcement learning parameter updates. |
| **RetailOps** | Full 4-service FastMCP microservice orchestration; LangGraph DAG execution; standard adapter. | Human interactive approval gates (deferred to Step 11). |

---

## 4. Common Evaluation Conditions

To ensure experimental parity, all approaches were evaluated under identical simulation conditions:
* **Evaluation Horizon**: $H = 28$ days ($d_{1914}$ to $d_{1941}$, April 25 to May 22, 2016).
* **M5 Store-Item Series**: Five diverse products from Walmart Store `CA_1`:
  - `CA_1_FOODS_1_004` (Fresh Grocery, Unit Price: $1.96, Wholesale Cost: $1.18, Mean Sales: 3.51 units/day)
  - `CA_1_FOODS_1_012` (Premium Grocery, Unit Price: $5.64, Wholesale Cost: $3.38, Mean Sales: 2.78 units/day)
  - `CA_1_HOUSEHOLD_1_007` (Household Cleaning, Unit Price: $1.48, Wholesale Cost: $0.89, Mean Sales: 2.21 units/day)
  - `CA_1_HOBBIES_1_004` (General Hobby Good, Unit Price: $4.64, Wholesale Cost: $2.78, Mean Sales: 1.76 units/day)
  - `CA_1_HOBBIES_1_008` (High-Velocity Craft, Unit Price: $0.48, Wholesale Cost: $0.29, Mean Sales: 10.97 units/day)
* **Disturbance Scenarios**:
  - `SCEN-01` (Normal Demand): Steady-state operations; $L = 7$ days; $k_{\text{init}} = 1.0$; reliability $0.95$.
  - `SCEN-02` (Demand Spike): $2.5\times$ customer demand surge; $L = 7$ days; $k_{\text{init}} = 1.0$; reliability $0.95$.
  - `SCEN-03` (Low Inventory): Initial stock depleted to $0.2\times$; $L = 7$ days; reliability $0.95$.
  - `SCEN-04` (Supplier Delay): Supplier lead time tripled to $L = 21$ days; reliability downgraded to $0.65$.
  - `SCEN-05` (Compound Stockout Risk): $2.5\times$ demand surge, $0.2\times$ initial stock, and $L = 14$ days (reliability $0.70$).
* **Common Operational Constraints**: $\text{MOQ} = 20$ units, $\text{MaxOQ} = 500$ units, daily holding rate $h = 0.001$ ($0.1\%$/day), fixed seed $42$.

---

## 5. Granular Per-Scenario Performance Results

The following tables present the mean performance across the five M5 series for each scenario without evaluative formatting:

### Scenario SCEN-01 (Normal Demand)
| Architecture Approach | Stockout Rate (%) | Service Level (%) | Mean Total Cost ($) | Total Lost Sales | Units Ordered |
| :--- | :--- | :--- | :--- | :--- | :--- |
| RetailOps MCP | 4.28% | 94.95% | $182.92 | 44 units | 744 units |
| Flowr Coordinator | 5.71% | 93.06% | $153.54 | 53 units | 639 units |
| WorkflowLLM Generative | 5.71% | 93.06% | $153.10 | 53 units | 632 units |
| Agentic Replenishment | 5.71% | 93.06% | $153.36 | 53 units | 668 units |
| Fixed-Threshold Base | 7.86% | 91.58% | $165.81 | 60 units | 682 units |

### Scenario SCEN-02 (Demand Spike 2.5x)
| Architecture Approach | Stockout Rate (%) | Service Level (%) | Mean Total Cost ($) | Total Lost Sales | Units Ordered |
| :--- | :--- | :--- | :--- | :--- | :--- |
| RetailOps MCP | 27.14% | 67.62% | $277.99 | 556 units | 1,112 units |
| Agentic Replenishment | 32.14% | 63.29% | $260.35 | 608 units | 1,057 units |
| WorkflowLLM Generative | 34.28% | 62.76% | $247.90 | 647 units | 971 units |
| Fixed-Threshold Base | 34.29% | 59.74% | $255.59 | 691 units | 972 units |
| Flowr Coordinator | 35.00% | 60.43% | $236.21 | 681 units | 914 units |

### Scenario SCEN-03 (Low Initial Stock 0.2x)
| Architecture Approach | Stockout Rate (%) | Service Level (%) | Mean Total Cost ($) | Total Lost Sales | Units Ordered |
| :--- | :--- | :--- | :--- | :--- | :--- |
| RetailOps MCP | 19.29% | 78.09% | $188.89 | 138 units | 749 units |
| WorkflowLLM Generative | 20.72% | 76.20% | $165.05 | 147 units | 658 units |
| Flowr Coordinator | 20.72% | 76.20% | $165.72 | 147 units | 660 units |
| Agentic Replenishment | 22.14% | 76.20% | $172.88 | 147 units | 731 units |
| Fixed-Threshold Base | 22.86% | 76.07% | $169.64 | 149 units | 717 units |

### Scenario SCEN-04 (Supplier Delay L=21d)
| Architecture Approach | Stockout Rate (%) | Service Level (%) | Mean Total Cost ($) | Total Lost Sales | Units Ordered |
| :--- | :--- | :--- | :--- | :--- | :--- |
| RetailOps MCP | 10.71% | 89.06% | $258.86 | 72 units | 1,032 units |
| Agentic Replenishment | 10.71% | 89.06% | $168.83 | 72 units | 725 units |
| WorkflowLLM Generative | 10.71% | 89.06% | $169.68 | 72 units | 682 units |
| Flowr Coordinator | 10.71% | 89.06% | $173.06 | 72 units | 698 units |
| Fixed-Threshold Base | 10.71% | 89.06% | $179.66 | 72 units | 731 units |

### Scenario SCEN-05 (Compound Stockout Risk)
| Architecture Approach | Stockout Rate (%) | Service Level (%) | Mean Total Cost ($) | Total Lost Sales | Units Ordered |
| :--- | :--- | :--- | :--- | :--- | :--- |
| RetailOps MCP | 45.71% | 49.34% | $320.79 | 781 units | 1,249 units |
| Agentic Replenishment | 53.57% | 41.29% | $247.19 | 931 units | 968 units |
| WorkflowLLM Generative | 55.71% | 40.16% | $246.79 | 951 units | 916 units |
| Flowr Coordinator | 55.71% | 39.43% | $242.93 | 967 units | 885 units |
| Fixed-Threshold Base | 55.71% | 36.97% | $226.78 | 967 units | 858 units |

---

## 6. Comprehensive Cross-Architecture Comparison

The table below provides the consolidated cross-architecture evaluation across all 25 runs (5 scenarios $\times$ 5 series) per system:

| Metric Dimension | RetailOps MCP | Flowr Coordinator | WorkflowLLM Generative | Agentic Replenishment | Fixed-Threshold Baseline |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Mean Stockout Rate (%)** | 21.43% | 25.57% | 25.43% | 24.86% | 26.29% |
| **Stockout Std Dev (%)** | $\pm 15.35\%$ | $\pm 18.32\%$ | $\pm 18.25\%$ | $\pm 17.65\%$ | $\pm 17.77\%$ |
| **Mean Service Level (%)** | 75.81% | 71.63% | 72.25% | 72.58% | 70.68% |
| **Service Level Std Dev (%)**| $\pm 16.96\%$ | $\pm 19.98\%$ | $\pm 19.34\%$ | $\pm 19.32\%$ | $\pm 20.35\%$ |
| **Mean Total Cost ($)** | $245.89 | $194.29 | $196.51 | $200.52 | $199.50 |
| **Mean Holding Cost ($)** | $12.35 | $6.92 | $7.15 | $7.38 | $6.84 |
| **Mean Reorder Cost ($)** | $233.54 | $187.37 | $189.36 | $193.14 | $192.66 |
| **Total Units Fulfilled** | 3,128 | 2,799 | 2,849 | 2,908 | 2,780 |
| **Total Lost Sales Units** | 1,591 | 1,920 | 1,870 | 1,811 | 1,939 |
| **Total Units Ordered** | 4,886 | 3,796 | 3,859 | 4,149 | 3,960 |
| **Constraint Violations** | 0 | 0 | 0 | 0 | 0 |
| **Conservation Balance Audit**| 100% Passed | 100% Passed | 100% Passed | 100% Passed | 100% Passed |

---

## 7. Implementation & Modularity Metrics

To evaluate software engineering attributes, implementation footprint was audited independently from simulation performance:

| Dimension | RetailOps MCP | Flowr Coordinator | WorkflowLLM Generative | Agentic Replenishment | Fixed-Threshold Baseline |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Architecture Classification** | Multi-Process FastMCP + LangGraph DAG | Centralized Reasoning Coordinator | Plan-then-Execute Generative Workflow | Single-Domain Autonomous Agent Loop | Mathematical Threshold Heuristic |
| **Implementation Files Count** | 5 files | 1 file | 1 file | 1 file | 1 file |
| **Implementation LOC** | 94 LOC (adapter) / ~1,000 LOC (services) | 150 LOC | 217 LOC | 76 LOC | 53 LOC |
| **Existing RetailOps Files Modified** | 0 lines | 0 lines | 0 lines | 0 lines | 0 lines |
| **External Dependencies** | `mcp`, `fastmcp`, `langgraph`, `openai`, `pydantic` | None (Standard library) | None (Standard library) | None (Standard library) | None (Standard library) |
| **Execution Time for 25 Runs (ms)** | 7.43 ms | 8.21 ms | 11.48 ms | 6.54 ms | 5.84 ms |
| **Average Time per Simulation (ms)** | 0.30 ms | 0.33 ms | 0.46 ms | 0.26 ms | 0.23 ms |

*Modularity Observations*:
1. **Zero Churn**: All three external architecture implementations were completely isolated inside `experiments/same_repo_comparison/`. Zero lines of production RetailOps code were altered.
2. **Implementation Footprint Comparison**:
   - `agentic_replenishment` required 76 LOC, implementing direct perception-action logic in a single class.
   - `workflowllm_generative` required 217 LOC due to the structural separation between plan schema modeling, Phase 1 plan generation, and Phase 2 dynamic parameter execution.
   - `flowr_coordinator` required 150 LOC, separating coordinator routing logic from modular domain tool functions.

---

## 8. Verification & Operational Integrity Audits

### 8.1 Constraint Violations Audit
Across all 125 simulation runs (25 runs $\times$ 5 approaches, representing 3,500 individual simulated operational days):
* Minimum Order Quantity compliance ($Q = 0$ or $Q \ge 20$): 100% compliant (0 violations).
* Maximum Capacity compliance ($Q \le 500$): 100% compliant (0 violations).
* Non-negative ending inventory ($I_t \ge 0$): 100% compliant (0 violations).
* Chronological delivery timing ($t + L$ arrivals): 100% compliant (0 violations).

### 8.2 Inventory Conservation Equation Audit
For every simulation run, conservation was verified:
$$\Delta = | I_{\text{ending}} - (I_{\text{initial}} + \text{Arrivals} - \text{Fulfilled}) |$$
**Result**: $\Delta = 0$ across all 125 runs. Zero inventory drift or numerical discrepancies occurred.

### 8.3 Deterministic Reproducibility Audit
When re-executed with random seed 42 under identical inputs, all five providers generated bit-for-bit identical outputs. Automated regression tests [`test_same_repo_comparison.py`](file:///E:/Repositories/RetailOPS-MCP/test_same_repo_comparison.py) pass with 100% success (43 total tests passed across the repository test suite).

---

## 9. Objective Operational Trade-Offs Observed Across Architectures

### 9.1 Factual Characterization by Architecture
* **RetailOps MCP**: Employed proportional lead-time safety buffering ($1.25 \times \bar{d} \times L$), recording a 21.43% mean stockout rate and 75.81% service level alongside a mean total operating cost of $245.89 across the evaluation matrix. Under demand spikes (`SCEN-02`), it recorded 556 lost sales units, and under compound disruption (`SCEN-05`), 781 lost sales units.
* **Flowr Coordinator Pattern**: Employed dynamic tool dispatch with early deferral when inventory runway was classified as low risk, recording a mean total operating cost of $194.29 alongside a 25.57% stockout rate and 71.63% service level. Under demand spikes (`SCEN-02`), it recorded 681 lost sales units, and under compound disruption (`SCEN-05`), 967 lost sales units.
* **WorkflowLLM Generative Pattern**: Executed a 5-step generative plan with dynamic parameter binding across scenario contexts, recording a 25.43% stockout rate, 72.25% service level, and a mean total operating cost of $196.51. Under demand spikes (`SCEN-02`), it recorded 647 lost sales units, and under compound disruption (`SCEN-05`), 951 lost sales units.
* **Agentic Replenishment Pattern**: Executed a direct single-domain reorder point heuristic in 76 LOC without intermediate microservice calls, recording a 24.86% stockout rate, 72.58% service level, and a mean total operating cost of $200.52. Under demand spikes (`SCEN-02`), it recorded 608 lost sales units, and under compound disruption (`SCEN-05`), 931 lost sales units.
* **Fixed-Threshold Baseline**: Executed a continuous review $(s, S)$ reorder point heuristic, recording a 26.29% stockout rate, 70.68% service level, and a mean total operating cost of $199.50. Under demand spikes (`SCEN-02`), it recorded 691 lost sales units, and under compound disruption (`SCEN-05`), 967 lost sales units.

### 9.2 Key Trade-Offs Observed
1. **Working Capital vs. Stockout Absorption**: Proportional safety buffering ($1.25 \bar{d} L$) recorded higher fulfillment during sudden surges than square-root buffering ($k \bar{d} \sqrt{L}$), but incurred an operating cost difference of $45 to $51 per series across the 28-day window.
2. **Supplier Latency Horizon Mismatch (`SCEN-04`)**: When supplier delivery latency ($L = 21$ days) approached the evaluation horizon ($H = 28$ days), orders placed after day 7 could not arrive before simulation close. All five systems recorded identical service levels (89.06%) and lost sales (72 units). RetailOps accumulated $258.86 in operating cost due to pipeline orders placed during the delay, compared to $168.83–$173.06 across the other three agentic patterns.

---

## 10. Threats to Validity & Non-Generalizability Declarations

1. **Specific M5 Subset Limitation**: Observations are drawn from five specific retail series in Walmart `CA_1` over 28 days. Results do not generalize universally across retail supply chains.
2. **Pattern Abstraction vs Original Models**: WorkflowLLM, Flowr, and Agentic Replenishment reproductions evaluate their published orchestration topologies, not their proprietary model checkpoints, private fine-tuned weights, or enterprise cloud infrastructures.
3. **Execution Environment Parity**: All runtimes were measured in a single local Python process on Windows without network latency. Runtime figures are reported strictly for completeness and do not constitute primary research claims.

---

*End of Step 10 Comparison Report. All four architectures are fully implemented, verified, and benchmarked.*
