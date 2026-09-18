# RetailOps Formal Evaluation Protocol

## 1. Purpose and Guiding Principles

This document establishes the experimental methodology and evaluation standards for the **RetailOps** research project. The objective is to produce reproducible, academically defensible evidence regarding enterprise AI decision orchestration, modularity, and systems overhead—**not** to claim algorithmic superiority in forecasting, pricing, or retail profitability.

### Academic Integrity Rules
1. **Never conflate architectural metrics with model quality**: Software engineering metrics (e.g. LOC changed, interface stability, process lifecycle latency, crash handling) must never be presented as proof of higher retail profit or superior forecasting accuracy.
2. **Strict evidence categorization**: Every assertion must be tagged as `literature`, `implementation`, or `experiment`.
3. **Transparent reporting of limitations**: Hardware environments, OS process costs, synthetic dataset scopes, and non-evaluated dimensions must be stated explicitly.
4. **Zero fabricated values**: Unmeasured quantities must be reported as `null` or `"not reported"`, never filled with illustrative or placeholder numbers.

---

## 2. Evaluation Dimensions and Standard Metrics

### 2.1 Integration Effort
Measures the developer effort and structural churn required to integrate an additional capability or modify existing pipelines.
* **Existing service files modified**: Must count only files belonging to existing services (target: 0).
* **Existing service LOC modified**: Non-comment, non-empty lines modified in existing services (target: 0).
* **Existing interfaces modified**: Changes to existing tool schemas, parameters, or return types (target: 0).
* **Orchestration files added/modified**: Explicitly distinguishes changes to the workflow runner from changes to domain services.
* **Cross-service dependencies introduced**: Imports or direct calls between sibling services (target: 0).
* **Developer time**: Reported only when measured under formal, timed observation protocols.

### 2.2 Extensibility
Evaluates whether a new specialized capability can be introduced into the workflow while preserving existing components.
* **Implementation isolation**: Evaluated via standalone file creation and process encapsulation.
* **Interface preservation**: Confirms that original pipelines (e.g. 4-stage) remain 100% operational without regressions.
* **Output schema compatibility**: Evaluates whether all standardized schema fields are populated and match deterministic expectations.
* **Output parity scope**: Output parity between baseline and MCP confirms identical algorithmic behavior across architectures; it does not indicate model quality.

### 2.3 Service Replacement
Evaluates whether an existing service can be substituted with an alternative implementation without ripple effects.
* **Upstream/downstream blast radius**: Files modified in sibling services (must be 0).
* **Interface contract adherence**: Verifies that replacement tools export identical MCP tool names and JSON schemas.
* **Downstream consumption rate**: Verifies that succeeding workflow stages consume replacement outputs without errors.

### 2.4 Performance and Overhead Dissection
Evaluates the latency distribution and runtime cost of process-based orchestration.
* **End-to-end latency**: Reported as `mean`, `median`, `p95`, and `std_dev` across $\ge 10$ repetitions.
* **Process lifecycle breakdown**: Explicitly distinguishes:
  1. OS process spawn time (`t_spawn`)
  2. MCP handshake and session entrance time (`t_init`)
  3. Domain service execution time (`t_exec`)
  4. Process termination and resource release (`t_shutdown`)
* **Overhead isolation**: Reusing persistent sessions amortizes process spawn and isolates pure IPC transport overhead.

### 2.5 Reliability and Fault Handling
Evaluates system resilience against deliberate fault injection across standardized scenarios:
* **Failure detection**: Verification that errors in tool execution or subprocess exits are detected without silent swallow.
* **Workflow status recording**: Expected status adherence (e.g. `failed_enrichment`, `failed_forecast`).
* **Partial-result preservation**: Confirms that completed outputs prior to the failure are retained in the result payload.
* **Downstream protection**: Confirms that subsequent nodes do not invoke downstream services after upstream failures.
* **Process cleanup**: Verification via `psutil` that terminated or failed subprocesses do not linger as zombie processes.
* **Terminology rule**: Distinguish between *graceful degradation/failure abortion* and *self-healing*. Do not use "self-healing" unless an automated restart/recovery loop is implemented and tested.

### 2.6 Model and Domain Quality
* If domain performance is evaluated, use standard statistical metrics: Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), Mean Absolute Percentage Error (MAPE), stockout rate, and realized gross margin.
* Explicitly state that orchestration framework design does not substitute for domain-specific model training.

---

## 3. Experimental Reproducibility Checklist

Every experiment must record and preserve:
1. **Environment**: OS version, CPU architecture, Python version, key package dependencies (`langgraph`, `mcp`, `psutil`, `pandas`).
2. **Workload**: Input category, product name, forecast horizon (`days_ahead`), deterministic data seeds.
3. **Execution Mode**: Explicitly declare whether Condition A (in-process baseline), Condition B (process-per-call MCP), or Condition C (persistent MCP session pool) was evaluated.
4. **Warm-up Policy**: Number of discarded warm-up runs vs. recorded benchmark repetitions.
5. **Artifacts**: Line-delimited raw execution logs (`raw_results.jsonl`), aggregated summary statistics (`summary.json`), and comprehensive narrative reports (`results.md`).
