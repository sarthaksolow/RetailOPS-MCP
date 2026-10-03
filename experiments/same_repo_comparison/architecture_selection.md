# Specification of Reproducible Research Architectures for M5 Operational Comparison

**Document ID**: `SPEC-ARCHITECTURE-SELECTION-V1`  
**Phase**: Step 9 — Selection and Specification of External Research Architectures  
**Evaluation Protocol**: [`PROTOCOL-EXP-FROZEN-V1`](file:///E:/Repositories/RetailOPS-MCP/experiments/evaluation_protocol.md)  
**Target Repository Workspace**: `experiments/same_repo_comparison/`  
**Date**: October 3, 2026  
**Status**: SPECIFICATION ONLY (Implementation and Execution Deferred to Step 10)

---

## 1. Executive Summary & Objective

The objective of Step 9 is to select and specify up to three reference architectures from peer-reviewed literature and preprints that can be faithfully reproduced within the local RetailOps environment.

The selected architectures will be evaluated under the identical M5 discrete-event inventory simulation environment established in Step 7 and executed in Step 8. This specification defines:
1. Source verification and bibliographic grounding.
2. Reproduction boundaries distinguishing reproducible architectural patterns from non-reproducible proprietary assets.
3. Common adapter contracts ensuring uniform input/output schemas across all systems.
4. Methodological fairness guarantees preventing information leakage or asymmetric tuning.

---

## 2. Source Grounding & Candidate Evaluation

Three candidate systems identified during the literature review were audited against rigorous reproduction criteria:
- **Criterion A (Operational Relevance)**: Direct applicability to retail forecasting, replenishment, or decision orchestration.
- **Criterion B (Descriptive Completeness)**: Architectural topology and decision rules described with sufficient clarity to permit an honest reproduction.
- **Criterion C (Local Implementability)**: Executable within the current local Python runtime without proprietary enterprise cloud dependencies.
- **Criterion D (Simulation Compatibility)**: Native adaptability to the discrete-event operational context (`OperationalDecisionContext`).
- **Criterion E (Architectural Distinctness)**: Structural divergence from RetailOps to provide meaningful comparative insights.

### 2.1 Candidate 1: Flowr (Centralized Reasoning Coordinator Pattern)
* **Bibliographic Source**:
  - *Title*: *Flowr -- Scaling Up Retail Supply Chain Operations Through Agentic AI in Large Scale Supermarket Chains*
  - *Authors*: Eranga Bandara, Ross Gore, Sachin Shetty, P. Siyambalapitiya, S. Rajapakse, I. Kularathna, P. Karunarathna, R. Mukkamala, P. Foytik, S. H. Bouk, A. Rahman, X. Liang, A. Hass, T. Hewa, N. W. Keong, K. De Zoysa, A. Withanage, N. Loganathan
  - *Year / Venue*: April 2026, arXiv preprint `arXiv:2604.05987` [cs.AI]
  - *URL*: [https://arxiv.org/abs/2604.05987](https://arxiv.org/abs/2604.05987)
* **Architectural Mechanism**:
  A centralized reasoning coordinator oversees cognitive decomposition across modular tools. Rather than following a rigid linear pipeline, the central coordinator evaluates incoming operational state, plans necessary invocations, calls domain-specific tools (forecasting, inventory checking, supplier verification) via structured interfaces, and synthesizes the final replenishment directive.
* **Selection Decision**: **SELECTED**.
  Flowr provides an authentic architectural comparison: a centralized dynamic coordinator versus RetailOps' compiled sequential LangGraph StateGraph DAG.

---

### 2.2 Candidate 2: WorkflowLLM (Generative Plan-then-Execute Pattern)
* **Bibliographic Source**:
  - *Title*: *WorkflowLLM: Enhancing Workflow Orchestration Capability of Large Language Models*
  - *Authors*: Shengda Fan, Xin Cong, Yuepeng Fu, Zhong Zhang, Shuyan Zhang, Yuanwei Liu, Yesai Wu, Yankai Lin, Zhiyuan Liu, Maosong Sun
  - *Year / Venue*: ICLR 2025 (arXiv submitted November 2024, `arXiv:2411.02052` [cs.CL])
  - *Affiliations*: Renmin University of China, Tsinghua University, ModelBest Inc.
  - *URL*: [https://arxiv.org/abs/2411.02052](https://arxiv.org/abs/2411.02052) | [GitHub](https://github.com/OpenBMB/WorkflowLLM)
* **Architectural Mechanism**:
  Two-stage generative workflow synthesis:
  1. *Workflow Generation*: The model dynamically generates an explicit multi-step execution plan (DAG or sequential workflow) based on intent and operational parameters.
  2. *Workflow Execution & Parameter Binding*: The generated plan is executed step-by-step, binding parameters dynamically across intermediate outputs.
* **Selection Decision**: **SELECTED**.
  WorkflowLLM provides a contrasting paradigm: runtime generative workflow synthesis rather than statically compiled execution topologies.

---

### 2.3 Candidate 3: Agentic Inventory Replenishment (Single-Domain Autonomous Agent Pattern)
* **Bibliographic Source**:
  - *Title*: *Agentic AI Framework for Smart Inventory Replenishment*
  - *Authors*: Toqeer Ali Syed, Salman Jan, Gohar Ali, Ali Akarma, Ahmad Ali, Qurat-ul-Ain Mastoi
  - *Year / Venue*: November 2025, *International Conference on Business and Digital Technology (ICBDT 2025)* / arXiv preprint `arXiv:2511.23366` [cs.AI]
  - *Affiliations*: National University of Computer and Emerging Sciences, Universiti Teknologi PETRONAS
  - *URL*: [https://arxiv.org/abs/2511.23366](https://arxiv.org/abs/2511.23366)
* **Architectural Mechanism**:
  Direct single-domain inventory replenishment agent. Rather than distributing cognitive operations across multiple microservices (catalog enricher, pricing strategy, forecasting server, replenishment server), a unified replenishment agent directly perceives inventory levels and demand signals, applies heuristic replenishment reasoning, and triggers purchase orders directly against supplier constraints.
* **Selection Decision**: **SELECTED**.
  This architecture provides a lean, unbundled baseline: it tests whether a specialized single-domain agent matches or outperforms complex multi-service orchestration frameworks.

---

## 3. Reproduction Matrix

The following matrix delineates the exact scope, components, and implementation confidence for each selected architecture:

| Architecture Identifier | Literature Source & Year | Original Operational Purpose | Reproduced Components | Non-Reproducible Components | Required Operational Inputs | Emitted Decision Output | Implementation Confidence | Known Limitations & Reproduction Boundaries |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`flowr_coordinator`** | Bandara et al. (2026), `arXiv:2604.05987` | Supermarket chain supply chain orchestration across distributed departments | Centralized reasoning coordinator; tool-mediated query routing; structured service dispatch; synthesis of replenishment decisions | Proprietary fine-tuned specialist LLM weights; commercial enterprise database connectors; multi-facility logistics networks | On-hand stock; in-transit orders; lead time; MOQ; historical mean daily demand; scenario metadata | Order quantity; order timing; reasoning narrative; domain-call trace | **MEDIUM**<br>(Clear orchestration pattern; original fine-tuned weights private) | Central coordinator reproduced via structured orchestration logic; relies on standardized local tool contracts rather than proprietary fine-tuned model checkpoints. |
| **`workflowllm_generative`** | Fan et al. (ICLR 2025), `arXiv:2411.02052` | Generalized API orchestration and generative workflow adaptation | Two-phase orchestration: explicit step-by-step workflow plan synthesis followed by sequential parameter binding and execution | WorkflowLlama fine-tuned checkpoint; large-scale 106k WorkflowBench dataset; open-domain Web API integration | On-hand stock; in-transit orders; lead time; MOQ; historical demand; active scenario disturbance | Planned workflow graph; order quantity; order timing; execution trace | **HIGH**<br>(Algorithmic plan-then-execute pattern is fully documented) | Plan generation is scoped to retail replenishment sub-operations; deterministic step-by-step executor emulates WorkflowLlama's structured API planner. |
| **`agentic_replenishment`** | Syed et al. (ICBDT 2025), `arXiv:2511.23366` | Autonomous retail inventory replenishment and supplier order initiation | Direct perception-action inventory loop; unified order calculation; supplier lead-time and MOQ compliance checks | Deep reinforcement learning policy weights; proprietary ERP database integrations; automated supplier contract negotiation | On-hand stock; pipeline in-transit inventory; lead time; MOQ; historical sales rate | Recommended order quantity; order urgency; stockout risk assessment | **HIGH**<br>(Direct domain replenishment heuristic is completely specified) | Operates as a focused single-node replenishment engine without multi-stage microservice overhead, evaluating the efficacy of direct inventory control. |

---

## 4. Architectural Boundaries & Reproduction Scope

To preserve scientific validity, this project makes no claim of creating full, commercial-grade replicas of the original research systems. Instead, it extracts and evaluates the **core decision and orchestration patterns** defined by each architecture:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        ARCHITECTURAL ORCHESTRATION SPECTRUM                            │
├─────────────────────────┬─────────────────────────┬────────────────────────────────────┤
│ Pattern Paradigm        │ Representative System   │ Structural Topology                │
├─────────────────────────┼─────────────────────────┼────────────────────────────────────┤
│ Compiled DAG Pipeline   │ RetailOps (LangGraph)   │ Fixed StateGraph sequential DAG    │
│ Central Coordinator     │ Flowr Pattern           │ Dynamic star topology coordinator  │
│ Generative Planner      │ WorkflowLLM Pattern     │ Plan-then-execute two-phase engine │
│ Single-Domain Direct    │ Agentic Replenishment   │ Monolithic single-node agent loop  │
│ Fixed Heuristic         │ Continuous Review (s,S) │ Deterministic mathematical formula │
└─────────────────────────┴─────────────────────────┴────────────────────────────────────┘
```

### 4.1 Flowr Reproduction Boundary
* **What is Reproduced**:
  - The centralized coordinator pattern where a central agent inspects state, requests inputs from specialized tool functions, and formulates the replenishment decision.
  - Cognitive decomposition separating inventory status assessment from replenishment calculation.
* **What Cannot Be Reproduced**:
  - The proprietary consortium of fine-tuned domain LLMs developed for specific commercial retail partners.
  - Multi-facility warehouse-to-store logistics network routing.
* **Necessary Assumptions**:
  - Local tool functions supply the domain responses using standardized formulas.
  - The coordinator operates deterministically given the context.

### 4.2 WorkflowLLM Reproduction Boundary
* **What is Reproduced**:
  - The two-phase pattern: generating an explicit operational plan (`AssessStock`, `ForecastDemandWindow`, `CalculateBuffer`, `EnforceConstraints`) and executing the generated plan sequentially.
  - Dynamic adaptation to scenario disturbance parameters during the planning phase.
* **What Cannot Be Reproduced**:
  - The 106,763-sample WorkflowBench dataset and full WorkflowLlama fine-tuning infrastructure.
* **Necessary Assumptions**:
  - The planning grammar generates structured retail replenishment steps compatible with the M5 environment.

### 4.3 Agentic Replenishment Reproduction Boundary
* **What is Reproduced**:
  - Direct perception of on-hand inventory, in-transit orders, and daily demand rate.
  - Direct calculation of order quantity without multi-service pipeline overhead.
  - Direct enforcement of supplier lead-time constraints and batch MOQ.
* **What Cannot Be Reproduced**:
  - Proprietary enterprise ERP database connectors.
  - Continuous online reinforcement learning updates during daily inference.
* **Necessary Assumptions**:
  - Replenishment parameters remain fixed during the 28-day evaluation window.

---

## 5. Common Adapter Interface Specification

All selected architectures must implement the standardized `BaseDecisionProvider` contract defined in [`experiments/m5_operational/decision_provider.py`](file:///E:/Repositories/RetailOPS-MCP/experiments/m5_operational/decision_provider.py):

```python
class BaseDecisionProvider(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier."""
        pass

    @abstractmethod
    def decide(self, context: OperationalDecisionContext) -> ReplenishmentDecision:
        """Evaluate operational context and return a standardized ReplenishmentDecision."""
        pass
```

### 5.1 Input Schema (`OperationalDecisionContext`)
Every architecture receives an identical, immutable daily state context containing:
* `series_id`: M5 store-item identifier (e.g. `CA_1_FOODS_1_004`).
* `current_day`: Evaluation day index $t \in [1, 28]$.
* `date`: Calendar date string (`YYYY-MM-DD`).
* `on_hand_inventory`: Physical ending inventory available for replenishment review ($I_t$).
* `in_transit_inventory`: Sum of all pending pipeline orders scheduled to arrive at $t' > t$.
* `mean_historical_daily_demand`: Historical daily demand $\bar{d}$ computed strictly from the 90-day pre-evaluation training split.
* `supplier_lead_time_days`: Supplier delivery latency $L$ (7, 14, or 21 days depending on scenario).
* `minimum_order_quantity`: Batch size lower bound ($\text{MOQ} = 20$).
* `maximum_order_quantity`: Warehouse capacity upper bound ($\text{MaxOQ} = 500$).
* `unit_cost`: Wholesale procurement cost per unit ($c_{\text{unit}}$).
* `unit_sell_price`: Retail sales price per unit ($p_{\text{sell}}$).
* `scenario_id`: Active disturbance identifier (`SCEN-01` to `SCEN-05`).

### 5.2 Output Schema (`ReplenishmentDecision`)
Every architecture must emit an identical decision structure:
* `order_quantity`: Non-negative integer $Q_t \ge 0$ (must satisfy $Q_t = 0$ or $\text{MOQ} \le Q_t \le \text{MaxOQ}$).
* `order_timing`: Standardized urgency classification (`"immediate"`, `"soon"`, or `"defer"`).
* `estimated_demand`: Forecasted demand value utilized in the reorder computation.
* `rationale`: Transparent explanatory string describing the decision logic.
* `provider_metadata`: Architecture-specific internal state trace (e.g., coordinator dispatch sequence, generated workflow plan, safety stock calculations).

---

## 6. Methodological Fairness Guarantees

To ensure strict parity and eliminate evaluation bias during the upcoming Step 10 benchmarks:
1. **Identical Out-of-Sample Observations**: All architectures will be evaluated on the exact same 5 M5 series over the exact same 28-day out-of-sample test window.
2. **Identical Disturbance Scenarios**: All architectures will face identical initial stock ($I_0$), demand multipliers, supplier delays, and reliability degradations across `SCEN-01` through `SCEN-05`.
3. **No Asymmetric Lookahead**: Zero architectures will have access to future customer demand $d_{t+1 \dots H}$.
4. **No Differential Parameter Tuning**: No architecture will be tuned against the evaluation window. All parameters must be fixed a priori based on historical training data or published heuristics.
5. **Strict Process Isolation**: Each architecture implementation will reside in its own dedicated, isolated module within `experiments/same_repo_comparison/`.

---

## 7. Bibliographic References

1. **Flowr**:  
   Bandara, E., Gore, R., Shetty, S., Siyambalapitiya, P., Rajapakse, S., Kularathna, I., Karunarathna, P., Mukkamala, R., Foytik, P., Bouk, S. H., Rahman, A., Liang, X., Hass, A., Hewa, T., Keong, N. W., De Zoysa, K., Withanage, A., & Loganathan, N. (2026). *Flowr -- Scaling Up Retail Supply Chain Operations Through Agentic AI in Large Scale Supermarket Chains*. arXiv preprint `arXiv:2604.05987` [cs.AI]. [https://arxiv.org/abs/2604.05987](https://arxiv.org/abs/2604.05987)

2. **WorkflowLLM**:  
   Fan, S., Cong, X., Fu, Y., Zhang, Z., Zhang, S., Liu, Y., Wu, Y., Lin, Y., Liu, Z., & Sun, M. (2025). *WorkflowLLM: Enhancing Workflow Orchestration Capability of Large Language Models*. International Conference on Learning Representations (ICLR 2025). arXiv preprint `arXiv:2411.02052` [cs.CL]. [https://arxiv.org/abs/2411.02052](https://arxiv.org/abs/2411.02052)

3. **Agentic Inventory Replenishment**:  
   Syed, T. A., Jan, S., Ali, G., Akarma, A., Ali, A., & Mastoi, Q. (2025). *Agentic AI Framework for Smart Inventory Replenishment*. International Conference on Business and Digital Technology (ICBDT 2025), Bahrain. Springer Nature. arXiv preprint `arXiv:2511.23366` [cs.AI]. [https://arxiv.org/abs/2511.23366](https://arxiv.org/abs/2511.23366)

4. **Walmart M5 Forecasting Competition**:  
   Makridakis, S., Spiliotis, E., & Assimakopoulos, V. (2022). *The M5 competition: Background, organization, and results*. International Journal of Forecasting, 38(4), 1483-1505. [https://doi.org/10.1016/j.ijforecast.2021.10.009](https://doi.org/10.1016/j.ijforecast.2021.10.009)

---

*Specification complete. Implementation and comparative evaluation are deferred to Step 10.*
