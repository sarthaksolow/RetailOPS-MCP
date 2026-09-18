# RetailOps Research Project: Experiment & Results Audit

**Project Title:** RetailOps: An MCP-Based Enterprise Decision Orchestration Framework for Autonomous Retail Operations  
**Date of Audit:** 2026-09-18  
**Audit Scope:** Tasks 01 through 09 completed artifacts, raw telemetry, benchmarks, and test suites.

---

## 1. Executive Summary

This audit catalogs all empirical evidence, experimental records, baseline comparisons, and literature analyses across the RetailOps repository prior to drafting the final research report and presentation.

### Core Principles Applied
1. **Measured Results vs. Interpretation:** Empirical measurements from RetailOps benchmarks are strictly separated from literature claims and architectural inferences.
2. **Experimental Isolation:** Protocol overhead is evaluated using an identical paired in-process Python baseline under deterministic conditions to isolate software systems costs from LLM network latencies.
3. **No Unsubstantiated Superiority:** External systems (Flowr, WorkflowLLM, Agentic Inventory Replenishment) are analyzed for architectural trade-offs without unsupported superiority claims, universal rankings, or negative proofs.

---

## 2. Comprehensive Inventory of Experiments (Tasks 01–09)

| Task / Experiment | Research Question | Metrics Measured | Result File Paths | Status | Suitable for Final Report |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **Task 01: Multi-Service Pipeline & Foundation** | Can specialized retail services (Catalog, Forecasting, Replenishment, Pricing) be orchestrated via LangGraph? | End-to-end execution success, state accumulation, step sequence | `test_integration.py`<br>`data/purchase_orders/` | Complete | Yes (validates functional architecture) |
| **Task 02: Research Telemetry & Instrumentation** | Can fine-grained telemetry capture service-level latencies and lifecycle status without leaking secrets? | Duration (ms), ISO timestamps, status enum, secret sanitization, JSONL persistence | `logs/telemetry.jsonl`<br>`client/telemetry.py`<br>`test_instrumentation.py` | Complete | Yes (underpins observability across all subsequent tasks) |
| **Task 03: Tightly Coupled Baseline** | What is the in-process baseline execution profile when running identical retail logic without MCP? | In-memory latency (ms), schema field parity, direct call overhead | `baseline/tightly_coupled.py`<br>`test_baseline_comparison.py` | Complete | Yes (provides the experimental control baseline) |
| **Task 04: Service Replacement** | Can a core domain service (Forecasting) be replaced with zero code churn in existing services? | Existing service LOC modified, sibling files modified, downstream decision consumption rate | `experiments/service_replacement/results.md`<br>`test_service_replacement.py` | Complete | Yes (demonstrates modular blast-radius containment) |
| **Task 05: Deterministic Runtime Benchmark** | What is the process lifecycle and execution overhead of process-per-call MCP vs. in-process execution? | Mean, median, P95, std dev runtime (ms), per-service breakdown across 30 runs | `experiments/performance_benchmark/summary.json`<br>`experiments/performance_benchmark/raw_results.jsonl`<br>`experiments/performance_benchmark/results.md` | Complete | Yes (quantifies process-per-call overhead on Windows) |
| **Task 06: Persistent MCP Sessions** | Can persistent session pooling amortize process startup and initialization costs? | Persistent runtime (ms), pool startup time (ms), pool shutdown (ms), speedup factor vs process-per-call | `experiments/persistent_mcp/summary.json`<br>`experiments/persistent_mcp/raw_results.jsonl`<br>`experiments/persistent_mcp/results.md`<br>`test_persistent_mcp.py` | Complete | Yes (demonstrates session pooling efficiency) |
| **Task 07: Fault Tolerance & Process Cleanup** | How does the architecture behave under tool exceptions, invalid outputs, and crashes, and are OS processes released? | Failure detection rate, downstream protection rate (`failed_enrichment`), partial result preservation, zombie processes (`psutil`) | `experiments/fault_tolerance/summary.json`<br>`experiments/fault_tolerance/raw_results.jsonl`<br>`experiments/fault_tolerance/results.md`<br>`test_fault_tolerance.py` | Complete | Yes (empirically validates reliable exception containment and process cleanup) |
| **Task 08: Pipeline Extensibility** | Can a 5th service (Supplier Intelligence) be added to the pipeline without modifying existing service code? | New service LOC, existing service LOC modified, orchestrator extension LOC, domain output parity across 11 fields | `experiments/extensibility/summary.json`<br>`experiments/extensibility/raw_results.jsonl`<br>`experiments/extensibility/results.md`<br>`test_extensibility.py` | Complete | Yes (validates non-invasive extensibility) |
| **Task 09: System Comparison & Framework** | How does RetailOps compare architecturally with Flowr, WorkflowLLM, and Agentic Replenishment? | Architectural dimensions, protocol usage, orchestration approaches, evaluation focus, reproducibility boundaries | `experiments/system_comparison/system_comparison_matrix.md`<br>`experiments/system_comparison/comparison_analysis.md`<br>`experiments/system_comparison/evaluation_framework.md`<br>`experiments/system_comparison/evidence_registry.json`<br>`experiments/system_comparison/results_summary.json`<br>`test_system_comparison.py`<br>`test_task09.py` | Complete | Yes (provides literature context and evaluation taxonomy) |

---

## 3. Inventory of Artifacts and File Types

### 3.1 Raw JSON / JSONL Telemetry
- `logs/telemetry.jsonl` (616 lines, 1.33 MB): Longitudinal execution telemetry across workflow executions.
- `experiments/performance_benchmark/raw_results.jsonl` (65 runs: 30 deterministic TC, 30 deterministic MCP, 5 production MCP).
- `experiments/persistent_mcp/raw_results.jsonl` (90 runs: 30 TC, 30 process-per-call MCP, 30 persistent MCP).
- `experiments/fault_tolerance/raw_results.jsonl` (60 fault injection runs across scenarios A through F).
- `experiments/extensibility/raw_results.jsonl` (10 paired runs comparing extended MCP vs extended baseline).

### 3.2 Evaluation Summaries (Structured JSON)
- `experiments/performance_benchmark/summary.json`: Descriptive statistics for Task 05.
- `experiments/persistent_mcp/summary.json`: Descriptive statistics and lifecycle breakdowns for Task 06.
- `experiments/fault_tolerance/summary.json`: Scenario-by-scenario recovery rates and process cleanup metrics for Task 07.
- `experiments/extensibility/summary.json`: Developer effort and parity metrics for Task 08.
- `experiments/system_comparison/results_summary.json`: Consolidated repository measurements for Task 09.
- `experiments/system_comparison/evidence_registry.json`: Source-linked evidence registry.

### 3.3 Markdown Reports & Documentation
- Detailed task reports: `experiments/*/results.md` (extensibility, fault_tolerance, performance_benchmark, persistent_mcp, service_replacement).
- Cross-system comparison documents: `experiments/system_comparison/*.md` (comparison analysis, comparison protocol, evaluation framework, matrix, tables).
- Methodological protocols: `experiments/evaluation_framework/evaluation_protocol.md`.

### 3.4 Automated Test Battery
- `test_instrumentation.py`: Verifies telemetry logging and secret scrubbing.
- `test_baseline_comparison.py`: Verifies baseline standalone execution and schema parity.
- `test_service_replacement.py`: Verifies forecasting replacement and blast radius containment.
- `test_performance_benchmark.py`: Verifies statistical calculations and schema constraints.
- `test_persistent_mcp.py`: Verifies persistent session lifecycle and reuse.
- `test_fault_tolerance.py`: Verifies scenarios A–F, downstream protection, and `psutil` process cleanup.
- `test_extensibility.py`: Verifies Supplier Intelligence integration and field-by-field parity.
- `test_system_comparison.py` & `test_task09.py`: Verifies comparison matrices, absence of superiority claims, and source grounding.
- `test_integration.py`: End-to-end client integration.

---

## 4. Analysis of Measured Results vs. External Literature

### 4.1 RetailOps Empirically Measured Results (Verified Facts)
1. **Service Replacement Blast Radius:** 0 lines of code modified in existing sibling services (`servers/forecasting/server.py` unchanged) when replacing forecasting logic.
2. **Process-per-Call Execution Overhead:** Spawning an independent FastMCP process per call on Windows NT adds ~1.5 to 2.2s per service invocation due to Python process creation and module importing, yielding a total pipeline mean latency of 11,489.28 ms.
3. **Persistent Session Amortization:** Reusing FastMCP subprocesses over persistent STDIO sessions reduces workflow latency to a mean of 37.75 ms (with a one-time pool startup time of 9,490.23 ms).
4. **Fault Recovery & Process Cleanup:** 100% downstream protection abort rate via explicit `failed_enrichment` state; 0 zombie processes remaining confirmed via OS-level `psutil` process table queries across 60 failure injections.
5. **Extensibility Churn:** Adding Supplier Intelligence required 183 LOC in the new service and 439 LOC in orchestrator extensions, while requiring 0 modifications to existing services.

### 4.2 External Paper Findings (Literature Context Only)
1. **Flowr (Bandara et al., 2026):** Decomposes supermarket supply chain operations across specialized cognitive agents with a central reasoning LLM, MCP-enabled supervisory interface, and pre-action governance loop (PAGRL).
2. **WorkflowLLM (Fan et al., 2025):** Evaluates dynamic generative workflow orchestration across 1,503 web APIs using fine-tuned models (WorkflowLlama).
3. **Agentic Replenishment (Syed et al., 2025):** Evaluates autonomous multi-agent reinforcement learning for inventory replenishment and supplier ordering in a middle-scale mart setting.

---

## 5. Identification of Missing Evidence, Duplicate Artifacts, and Gaps

1. **Duplicate / Transitional Directories:**
   - Both `experiments/flowr_comparison/` (Flowr-only, created initially in Task 09) and `experiments/system_comparison/` (comprehensive 4-system analysis, created subsequently) exist.
   - *Status:* `experiments/system_comparison/` is the canonical multi-system evaluation directory. `experiments/flowr_comparison/` remains preserved to ensure backward compatibility with `test_task09.py`.
2. **Model Quality Boundary:**
   - Algorithmic forecast accuracy (MAE/RMSE) and commercial retail profitability (inventory holding cost reduction) are intentionally not claimed as contributions of RetailOps, as RetailOps evaluates systems-level software orchestration.
3. **Hardware / Environment Specificity:**
   - All latency measurements reflect a single-node Windows testbed communicating over STDIO. Network-distributed MCP latency (e.g. over SSE / HTTP) is not evaluated.
4. **Unsupported Claims Check:**
   - Confirmed: Zero claims of universal superiority, zero rankings/scores, zero "sub-2ms" protocol claims, zero claims of complete memory/security isolation, and zero unverified 95% compliance claims for external systems exist in the active reports.

---

## 6. Readiness Assessment

| Evaluation Criterion | Status | Notes |
| :--- | :---: | :--- |
| **All Tasks 01–09 Complete** | **YES** | All 9 tasks have verified implementations, benchmarks, or structured literature analyses. |
| **Raw Telemetry Available** | **YES** | Raw JSONL files present for Tasks 02, 05, 06, 07, 08. |
| **Statistical Summaries Present** | **YES** | Formal `summary.json` files present across all benchmark tasks. |
| **Regression Battery Passing** | **YES** | The targeted regression battery covering system comparison, Flowr validation, extensibility, and performance benchmarks passed all 43 tests. |
| **Academic Guardrails Enforced** | **YES** | Strict uncertainty labels, neutral comparison matrix, and clear separation of model quality from orchestration quality. |

### Conclusion
**The audited artifacts and targeted verification results indicate that the repository is ready for results consolidation. The final report should state the remaining experimental limitations and scope boundaries.**
