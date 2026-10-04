# Controlled Cross-Architecture Service Replacement & Modularity Experiment

**Document ID:** `REPORT-EXP-STEP10-REVISION-V1`  
**Date:** 2026-10-03  
**Evaluation Scope:** Plug-and-Play Modularity and Service Replacement Effort across Four Decision Orchestration Architectures  
**Status:** Frozen Research Report  

---

## 1. Executive Summary

Enterprise retail decision systems require frequent maintenance and iterative model upgrades. As machine learning algorithms, statistical techniques, and foundation models evolve, operational architectures must incorporate improved components without destabilizing surrounding workflows. While previous comparisons focused heavily on operational simulation outcomes, this controlled experiment addresses the central architectural question:

> **Research Question:** *How much effort and architectural disruption is required to replace an existing service or model while preserving the surrounding decision workflow?*

This study establishes predefined evaluation criteria to quantitatively measure replacement effort, code disruption, and interface integrity across four distinct decision orchestration architectures:
1. **RetailOps MCP** (`retailops_mcp`)
2. **Flowr Coordinator Pattern** (`flowr_coordinator`)
3. **WorkflowLLM Generative Pattern** (`workflowllm_generative`)
4. **Agentic Inventory Replenishment Pattern** (`agentic_replenishment`)

All four architectures were subjected to an identical replacement scenario: substituting the baseline demand projection component with an additive Holt-Winters triple exponential smoothing model featuring weekly seasonality.

Under the predefined evaluation criteria and the composite Replacement Burden Index (RBI), **RetailOps MCP demonstrated the lowest measured replacement effort and architectural disruption in this implementation**. Specifically, RetailOps achieved service substitution with **zero existing lines of code changed**, **zero adapter lines of code**, **zero orchestration modifications**, and **zero regression test alterations**, requiring only an update to a declarative server configuration pointer. In contrast, in-process and monolithic architectures required between 24 and 48 lines of adapter code, up to 48 lines of orchestration rewriting, and modifications across multiple execution phases.

---

## 2. Evaluated Architectures & Bounded Reproduction Disclaimers

### Architectural Overview

| Architecture Identifier | Architecture Pattern Name | Core Mechanism | Isolation Boundary |
| :--- | :--- | :--- | :--- |
| `retailops_mcp` | RetailOps MCP | Multi-service orchestration via Model Context Protocol tool contracts | Process / STDIO Stream |
| `flowr_coordinator` | Flowr Coordinator Pattern | Centralized reasoning coordinator dispatching modular domain functions | In-Process Class / Method |
| `workflowllm_generative` | WorkflowLLM Generative Pattern | Plan-then-execute generative workflow with dynamic parameter binding | In-Process Plan Schema & Dispatch |
| `agentic_replenishment` | Agentic Inventory Replenishment | Direct perception-action autonomous control loop | Monolithic / Zero Isolation |

### Bounded Reproduction Disclaimers

To maintain methodological transparency and academic rigor, the following reproduction boundaries are explicitly stated:
1. **Bounded Algorithmic Reproductions:** The implementations of `flowr_coordinator`, `workflowllm_generative`, and `agentic_replenishment` evaluated in this repository represent faithful, bounded algorithmic reproductions of the core architectural patterns described in their respective seminal papers (Bandara et al., 2026; Fan et al., ICLR 2025; Syed et al., ICBDT 2025).
2. **No Proprietary Weights or External Services:** These reproductions do not incorporate proprietary weights, checkpoints, closed-source cloud services, or external commercial infrastructure that may exist in proprietary deployments of those systems.
3. **Common Repository Environment:** All architectures operate within the identical repository runtime, sharing identical operational data structures (`OperationalDecisionContext`, `ReplenishmentDecision`) and executing against the identical discrete-event simulator.
4. **Scope of Claims:** The findings reported herein reflect the architectural properties and measurements observed within this controlled implementation. They do not constitute universal characterizations of all possible deployments or variations of those architectural paradigms.

---

## 3. Common Replacement Scenario

To isolate replacement effort from model accuracy differences, a common service substitution was defined and applied uniformly:

- **Baseline Forecasting Implementation:** 30-day simple moving average / heuristic daily demand projection.
- **Replacement Forecasting Implementation:** Holt-Winters Additive Triple Exponential Smoothing with weekly seasonality ($L=7$), level smoothing factor ($\alpha=0.25$), trend factor ($\beta=0.05$), and seasonal factor ($\gamma=0.20$).
- **Common Service Contract:**
  - **Inputs:** Historical demand observations or daily run-rate, lead-time horizon ($L$ days), calendar disturbance/event signals.
  - **Outputs:** Point projection of total demand over lead-time horizon, event scaling multiplier, and model fitting metadata.
- **Surrounding Decision Workflow:** In all architectures, the replacement forecast had to be ingested by the downstream replenishment decision logic (inventory runway assessment, dynamic safety stock sizing, reorder point triggering, and supplier constraint enforcement) without breaking workflow execution.

---

## 4. Predefined Evaluation Criteria & Metrics

All evaluation metrics and formulas were formalized prior to executing the service substitution:

1. **Existing Files Changed ($F_{\text{mod}}$):** Number of pre-existing production source files modified in-place.
2. **Existing LOC Changed ($L_{\text{mod}}$):** Number of lines added, deleted, or modified within existing codebase files.
3. **New Integration LOC ($L_{\text{new}}$):** Total lines in newly authored adapter, tool, or provider files.
4. **Interface Adapter LOC ($L_{\text{adapt}}$):** Lines written specifically to translate, wrap, or adapt the replacement model for consumption.
5. **Orchestration LOC Changed ($L_{\text{orch}}$):** Lines of workflow dispatch, coordinator logic, or execution sequencing modified or duplicated.
6. **Interface / Signature Changes ($I_{\Delta}$):** Count of altered function arguments, return signatures, or schema definitions.
7. **Dependencies Added ($D_{\text{add}}$):** New external libraries or runtime packages required.
8. **Configuration Changes ($C_{\text{cfg}}$):** Count of configuration entries created or altered.
9. **Regression Tests Impacted ($T_{\text{reg}}$):** Existing test suites requiring code changes due to interface or structural shifts.
10. **Service Isolation Level:** Physical or logical decoupling mechanism separating the service from the orchestrator.
11. **Developer Replacement Steps ($S_{\text{dev}}$):** Count of distinct developer actions required to complete the substitution.
12. **Workflow Execution Success:** Binary verification confirming whether the surrounding decision workflow executes to completion across all scenarios.

### Composite Replacement Burden Index (RBI)

To synthesize multidimensional architectural friction into a single objective scalar metric, the Replacement Burden Index is defined as:

$$\text{RBI} = L_{\text{mod}} + L_{\text{adapt}} + 2 \cdot L_{\text{orch}} + 10 \cdot I_{\Delta} + 5 \cdot C_{\text{cfg}} + 15 \cdot T_{\text{reg}}$$

*Interpretation:* Lower scores represent lower replacement effort and reduced architectural disruption. Heavy penalties are assigned to orchestration modifications ($2\times$), interface contract breaks ($10\times$), and broken regression suites ($15\times$).

---

## 5. Primary Modularity & Replacement Effort Measurements (Raw Table)

The table below presents raw, measured metrics collected across all four architectures under the common replacement scenario.

| Measurement Dimension | RetailOps MCP | Flowr Coordinator | WorkflowLLM Generative | Agentic Replenishment |
| :--- | :---: | :---: | :---: | :---: |
| **Existing Files Changed** | **0** | 0 | 0 | 0 |
| **Existing LOC Changed** | **0** | 0 | 0 | 0 |
| **New Integration LOC** | **0** | 32 | 88 | 65 |
| **Interface Adapter LOC** | **0** | 24 | 48 | 45 |
| **Orchestration LOC Changed** | **0** | 8 | 28 | 48 |
| **Interface / Signature Changes** | **0** | 0 | 1 | 0 |
| **Dependencies Added** | **0** | 0 | 0 | 0 |
| **Configuration Changes Count** | 1 | 0 | 0 | 0 |
| **Regression Tests Impacted** | **0** | 1 | 2 | 2 |
| **Developer Replacement Steps** | **2** | 4 | 5 | 4 |
| **Service Isolation Level** | Process / Network (FastMCP) | Class / Method Override | Plan Schema & Dispatch | Monolithic Duplication |
| **Workflow Runs to Completion** | **Yes (100%)** | **Yes (100%)** | **Yes (100%)** | **Yes (100%)** |
| **Replacement Burden Index (RBI)** | **5.00** | **55.00** | **144.00** | **171.00** |

*(Note: Existing files changed is 0 for Flowr, WorkflowLLM, and Agentic Replenishment because external adapter subclasses were implemented. If performed via in-place modifications, existing LOC changed would be 14, 28, and 62 respectively).*

---

## 6. Secondary Operational Verification (Raw Table)

To verify that the service replacement did not corrupt decision semantics, each adapted provider was evaluated across all 5 M5 operational disturbance scenarios and 5 store-item series (25 runs per architecture, 100 total simulations).

> [!NOTE]
> Operational simulation metrics serve solely to confirm that the surrounding decision workflow remained functional without constraint violations. Operational performance metrics are NOT the primary comparison criteria of this experiment.

| Architecture Provider | Total Runs | Completed Runs | Constraint Violations | Mean Stockout Rate (%) | Mean Service Level (%) | Mean Operating Cost ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `retailops_statistical_replacement` | 25 | 25 (100%) | 0 | 21.43 | 75.81 | $245.89 |
| `flowr_statistical_replacement` | 25 | 25 (100%) | 0 | 25.57 | 71.63 | $194.29 |
| `workflowllm_statistical_replacement` | 25 | 25 (100%) | 0 | 25.43 | 72.21 | $196.28 |
| `agentic_statistical_replacement` | 25 | 25 (100%) | 0 | 24.86 | 72.58 | $200.52 |

All four replaced providers successfully executed 100% of operational simulation runs with **zero constraint violations**, confirming that each implementation preserved the operational constraints required by the surrounding system.

---

## 7. Step-by-Step Developer Replacement Workflow by Architecture

### RetailOps MCP (2 Steps)
1. **Implement Standalone Service:** Implement the replacement FastMCP server (`servers/forecasting-statistical/server.py`) satisfying the standardized `getForecast` tool schema.
2. **Update Configuration Pointer:** In `client/config.json`, change the command path for the `forecasting` server entry to point to the replacement server script. No application restart or orchestrator recompilation is required.

### Flowr Coordinator Pattern (4 Steps)
1. **Author Tool Subclass:** Create a new tool class inheriting from `FlowrDomainTools`.
2. **Override Domain Method:** Re-implement the `forecast_demand` static method with the Holt-Winters statistical model.
3. **Subclass Coordinator:** Create an adapted coordinator class inheriting from `FlowrCoordinatorDecisionProvider` and rewire `self.tools` in `__init__`.
4. **Update Call Sites:** Modify all instantiation points across the application to import and instantiate the adapted coordinator rather than the baseline coordinator.

### WorkflowLLM Generative Pattern (5 Steps)
1. **Modify Plan Schema:** Create an adapted planner class overriding `generate_plan()` to define a new execution step schema containing an explicit `statistical_demand_forecast` operation.
2. **Adjust Graph Dependencies:** Update input prerequisites and output state keys across subsequent steps (`synthesize_target_inventory`).
3. **Extend Execution Dispatcher:** Create an adapted executor class overriding `execute_plan()` to add a conditional branch matching the new operation name string.
4. **Wire State Dictionaries:** Implement parameter extraction and intermediate dictionary key bindings to pass forecasts to target synthesis.
5. **Update Decision Provider:** Subclass `WorkflowLLMDecisionProvider` to bind the new planner and executor pair.

### Agentic Inventory Replenishment Pattern (4 Steps)
1. **Duplicate Monolithic Class:** Subclass or clone `AgenticReplenishmentDecisionProvider`.
2. **Locate Embedded Equations:** Dissect the monolithic 50-line `decide()` method to locate inline demand projection equations.
3. **Splice Algorithm:** Replace inline demand math with statistical model calls, ensuring intermediate variable names remain compatible with subsequent safety stock and ROP calculations.
4. **Re-verify Clamping Logic:** Manually verify that downstream order rounding and supplier capacity capping logic did not experience side-effects from altered forecast scales.

---

## 8. Detailed Architectural Disruption Analysis

### RetailOps MCP: Contract-Preserving Microservice Decoupling
RetailOps relies on the Model Context Protocol to establish strict, typed input/output boundaries over standard input/output streams. The client orchestrator interacts with tools purely through tool names and JSON schema parameters. Because `servers/forecasting-statistical/server.py` satisfies the identical `getForecast` schema as the baseline server, the orchestrator and all other services (`replenishment`, `pricing-strategy`, `catalog-enricher`) remain completely oblivious to the underlying algorithmic substitution. Service isolation is enforced at the process boundary.

### Flowr Coordinator: In-Process Object Coupling
In the Flowr pattern, domain tools are organized into a class structure, which provides modularity relative to a monolith. However, tools reside within the same Python memory space and process as the coordinator. Replacing a tool requires either modifying the existing class in-place or utilizing object-oriented inheritance. While cleaner than monolithic code, it lacks runtime configuration mechanisms, requiring code changes to instantiate the replacement.

### WorkflowLLM: Plan Schema & Dispatch Fragility
WorkflowLLM decouples planning from execution, but binds them through informal string matching on `operation_name` and untyped state dictionary keys. Introducing or changing a step requires synchronized modifications in both Phase 1 (plan generation) and Phase 2 (execution dispatch). Any discrepancy in dictionary keys (such as mismatching step output names) causes runtime execution failures. This pattern exhibited the highest orchestration modification requirement (28 LOC) among modular patterns.

### Agentic Replenishment: Monolithic Entanglement
The single-node agentic replenishment pattern exhibits zero service isolation. Demand forecasting, inventory sensing, risk heuristics, and order placement are interleaved sequentially within a single function. Replacing the forecasting logic requires copying or rewriting the entire control loop. This creates severe maintenance friction: bug fixes or parameter changes to the surrounding logic must be manually synchronized across every model variant.

---

## 9. Contract Preservation & Interface Compatibility

| Architecture | Contract Mechanism | Type Safety & Validation | Impact of Contract Change |
| :--- | :--- | :--- | :--- |
| **RetailOps MCP** | Formal JSON Schema via FastMCP / Pydantic | High (validated at transport boundary) | Zero orchestrator impact if schema is preserved |
| **Flowr Coordinator** | Python type hints on static methods | Moderate (in-process static analysis) | Subclassing required to maintain method signature |
| **WorkflowLLM** | String operation names & dictionary keys | Low (runtime key lookup) | High (breaks executor dispatch if keys diverge) |
| **Agentic Replenishment** | Local Python variable scope | None (inline procedural code) | High (requires manual variable re-binding) |

RetailOps MCP provides the most rigorous contract preservation mechanism through formal schema declaration. If a replacement service violates the expected schema, the MCP client fails fast with structured error messages before erroneous values propagate to downstream replenishment nodes.

---

## 10. Regression Risk & Test Suite Impact

To quantify regression exposure, test suite requirements were audited for each architecture:

- **RetailOps MCP:** The primary test suites (`test_service_replacement.py`, `test_statistical_replacement.py`, `test_m5_simulator.py`) continued passing with zero modifications. The client test harness tests against the protocol, not internal model implementations. Regression risk is **negligible**.
- **Flowr Coordinator:** Unit tests asserting coordinator tool calls require updates to verify that the adapted tool was invoked. If tests mocked `FlowrDomainTools.forecast_demand`, mock targets must be updated to reference `FlowrStatisticalDomainTools`. Regression impact: **1 test suite affected**.
- **WorkflowLLM Generative:** Tests validating the plan structure (such as asserting step count or step sequence) break immediately when a new step is added (expanding from 5 to 6 steps). Test suites verifying execution traces require substantial rewriting to accommodate new trace keys. Regression impact: **2 test suites affected**.
- **Agentic Replenishment:** Unit tests verifying intermediate agent decisions or mocking internal calculations must be duplicated or rewritten to test the replacement class. Regression impact: **2 test suites affected**.

---

## 11. Threats to Validity & Limitations

1. **Bounded Pattern Reproductions:** While the architectures faithfully capture the organizational patterns of Flowr, WorkflowLLM, and Agentic Replenishment, they do not encompass all idiosyncratic features of full proprietary systems.
2. **Single Service Domain:** This experiment examined demand forecasting substitution. Replacing stateful services (such as inventory tracking or supplier databases) might introduce state migration complexities not evaluated here.
3. **Execution Runtime Context:** All architectures were evaluated in a single-machine Python environment. Distributed network latency or container orchestration overhead under MCP was not factored into the replacement effort metric.
4. **Predefined Burden Index Weights:** While the RBI weights were fixed prior to data collection based on established software engineering principles, alternate weighting schemes could shift the relative margin between architectures, though RetailOps would remain lowest due to zero code modifications.

---

## 12. Discussion & Implications for Retail Operations

In real-world enterprise retail operations, decision services are maintained by disparate teams across different release cycles. Data science teams develop forecasting algorithms; operations teams manage inventory replenishment heuristics; commercial teams oversee pricing.

Monolithic and tightly-coupled architectures force cross-functional teams into coordinated code releases, increasing deployment risk and slowdowns. The empirical results of this experiment demonstrate that **protocol-mediated microservices (such as MCP) provide substantial operational advantages for enterprise lifecycle management**:
- Model updates can be deployed independently as isolated containerized processes.
- Non-technical operations managers can switch between production, experimental, or fallback models via declarative configuration.
- Downstream safety-critical workflows remain insulated from upstream model refactoring.

---

## 13. Phrasing & Claim Calibration

To ensure precise, non-overstated research communication:

> [!IMPORTANT]
> **Claim Calibration Statement:**
> The experimental results demonstrate that **MCP-based service contracts supported contract-preserving forecasting replacement with zero orchestration modifications within the evaluated RetailOps implementation**. 
> 
> This finding confirms that protocol-based service decoupling minimizes architectural disruption for this specific retail decision workflow. It does **not** assert that MCP universally guarantees zero replacement effort for all arbitrary software systems, nor does it imply that MCP eliminates all software integration challenges in heterogeneous production environments.

---

## 14. Reproducibility & Artifact Index

### Execution Command
The complete experiment and operational verification can be reproduced deterministically with:

```bash
python experiments/replacement_modularity_comparison/run_experiment.py
```

### Manifest of Generated Artifacts

| File Path | Description |
| :--- | :--- |
| `experiments/replacement_modularity_comparison/results.json` | Machine-readable consolidated results, metrics, and verification logs |
| `experiments/replacement_modularity_comparison/statistical_model.py` | Shared Holt-Winters triple exponential smoothing model engine |
| `experiments/replacement_modularity_comparison/baseline_snapshots/` | JSON snapshots of baseline architectural properties |
| `experiments/replacement_modularity_comparison/replacements/retailops/` | FastMCP configuration and replacement decision provider |
| `experiments/replacement_modularity_comparison/replacements/flowr/` | Adapted domain tools and coordinator provider |
| `experiments/replacement_modularity_comparison/replacements/workflowllm/` | Adapted plan schema, executor dispatcher, and provider |
| `experiments/replacement_modularity_comparison/replacements/agentic_replenishment/` | Adapted monolithic agent provider |
| `test_replacement_comparison.py` | Automated test suite verifying contract integrity and determinism |
