# Empirical Evaluation: Fault Tolerance and Failure Recovery in RetailOps (Task 07)

## Executive Summary

This empirical evaluation measures the resilience, error detection, partial-result preservation, and downstream protection of the **RetailOps** MCP-based orchestration framework under injected failures. A total of **60 controlled workflow executions** were conducted across **6 failure scenarios** (10 repetitions per scenario) under local deterministic conditions.

Preliminary empirical evidence indicates:
- **Failure Detection Rate**: **100.0%** across all 60 test runs.
- **Expected Behavior Rate**: **100.0%** conformance to expected pipeline halting and state recording semantics.
- **Partial-Result Preservation Rate**: **100.0%** across all scenarios where prior stages succeeded.
- **Downstream Protection Rate**: **100.0%** prevention of downstream stages executing against missing or failed predecessor outputs.
- **Cleanup Success Rate**: **100.0%** clean subprocess termination and session recycling without deadlocks, hanging threads, or unclosed file handles.

---

## Experimental Environment

- **Operating System**: Windows 11 (`win32` / `nt`)
- **Python Runtime**: Python 3.12.0
- **Orchestration Transport**: MCP STDIO
- **Sample Repetitions**: $N = 10$ repetitions per scenario ($N_{total} = 60$ measured executions)
- **Input Workload**: `Samsung TV` (maps deterministically to category `electronics`)

---

## Summary of Empirical Metrics

The table below summarizes measured quantitative metrics aggregated by failure scenario:

| Scenario | Target Service | Injected Mode | Detection Rate (%) | Expected Behavior (%) | Partial Preservation (%) | Downstream Protection (%) | Context Cleanup (%) | OS Process Cleanup (%) | Mean Latency (ms) | Latency Range [Min, Max] (ms) | Primary Error Taxonomy |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Scenario A** | Catalog Enricher | `tool_error` | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 2,789.02 | [2,558.01, 3,390.52] | `tool_level_exception` |
| **Scenario B** | Forecasting | `tool_error` | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 4,508.98 | [4,142.24, 5,063.63] | `tool_level_exception` |
| **Scenario C** | Replenishment | `tool_error` | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 6,915.58 | [6,479.32, 7,613.33] | `tool_level_exception` |
| **Scenario D** | Pricing Strategy | `tool_error` | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 10,241.71 | [8,920.61, 11,373.94] | `tool_level_exception` |
| **Scenario E** | Replenishment (Persistent) | `tool_error` | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 10,369.61 | [9,150.39, 11,836.03] | `tool_level_exception` |
| **Scenario F** | Forecasting (Process Crash) | `crash_exit` | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 4,531.95 | [3,427.96, 6,134.15] | `subprocess_termination` |
| **Overall** | *Aggregated* | *All Modes* | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **6,559.48** | **[2,558.01, 11,836.03]** | — |

---

## Detailed Scenario Analysis

### Scenario A: Catalog Enricher Failure
- **Behavior**: The Enricher tool generates an exception (`tool_error`). The LangGraph `enrichment_node` catches the failure, records `"enrich"` in `failed_steps`, logs the error in `errors`, and explicitly sets `state["workflow_status"] = "failed_enrichment"`.
- **Hardened Downstream Protection**: Each subsequent downstream node (`forecasting_node`, `replenishment_node`, `pricing_node`) explicitly validates `if "failed" in state.get("workflow_status", ""): return state`. Downstream nodes immediately abort without initiating MCP subprocess invocations or tool calls, creating a strict architectural guarantee that is fully independent of whether fallback data exists for category `"general"`.
- **Mean Latency**: 2,789.02 ms (demonstrating significant latency reduction from immediate fail-fast termination before calling forecasting).

### Scenario B: Forecasting Service Failure
- **Behavior**: Catalog enrichment completes successfully, resolving `Samsung TV` to `category = "electronics"`, `brand = "Samsung"`. The forecasting service subsequently returns an injected tool error.
- **Partial Preservation**: The final workflow state retains the successful enrichment result in both `result["enrichment"]` and `result["partial_result"]["enrichment"]`.
- **Downstream Protection**: `replenishment_node` checks `workflow_status == "failed_forecast"` and exits immediately without issuing an MCP call. `pricing_node` similarly checks `"failed" in workflow_status` and aborts.
- **Mean Latency**: 4,508.98 ms.

### Scenario C: Replenishment Service Failure
- **Behavior**: Both Catalog Enrichment and Forecasting stages complete normally. The replenishment service raises an injected tool exception.
- **Partial Preservation**: Both enrichment data and forecast demand values (`final_forecast = 300.15`) are preserved in `result["partial_result"]`.
- **Downstream Protection**: `pricing_node` recognizes `workflow_status == "failed_replenishment"` and skips execution, shielding retail pricing algorithms from computing discounts without replenishment stock context.
- **Mean Latency**: 6,915.58 ms.

### Scenario D: Pricing Strategy Failure
- **Behavior**: Stages 1 through 3 execute cleanly. The terminal stage (Pricing Strategy) raises an injected tool exception.
- **Partial Preservation**: The final execution output contains full, valid payloads for Catalog Enrichment, Forecasting, and Replenishment Reorder Quantities (`reorder_qty = 250`).
- **Mean Latency**: 10,241.71 ms (reflecting execution through 3 complete upstream services prior to error detection).

### Scenario E: Persistent MCP Tool Failure & Recovery
- **Behavior**: Injected inside a `PersistentMCPSessionPool` context where long-lived STDIO sessions are shared across requests. Replenishment tool execution fails.
- **Recovery & Isolation**: The exception is caught at the session boundary and recorded in state. Subsequent requests across the same persistent session pool execute without residual corruption, and when the context manager exits, all 4 persistent subprocesses close cleanly with 0 orphaned OS processes verified via `psutil`.
- **Mean Latency**: 10,369.61 ms.

### Scenario F: Process Crash / Abrupt Subprocess Termination
- **Behavior**: During tool invocation, the forecasting server process calls `os._exit(1)`. The OS abruptly tears down the standard I/O pipes.
- **Fault Trapping**: The MCP `stdio_client` and `anyio.TaskGroup` detect pipe closure and raise an exception group. The orchestrator catches the exception, classifies it as `subprocess_termination`, appends it to `errors`, updates `workflow_status = "failed_forecast"`, and terminates the pipeline without deadlock, verified to leave 0 dangling child processes.
- **Mean Latency**: 4,531.95 ms.

---

## Architectural Insights and Tradeoffs

1. **Explicit Precondition Guards vs. Blind Edge Transitions**:
   In LangGraph sequential workflows, adding defensive checks at the entry of each node (`if "failed" in state["workflow_status"]: return state`) provides robust downstream protection against corrupt state propagation.
2. **Partial Result Snapshots in Orchestrator Telemetry**:
   Preserving intermediate artifacts (`partial_result`) ensures that operational retail systems retain visibility into demand projections even if fulfillment or pricing systems experience temporary outages.
3. **Subprocess Termination Resilience in AnyIO/MCP**:
   MCP Python SDK relies on AnyIO task groups. Wrapping MCP `stdio_client` blocks in targeted exception handlers ensures that severe operating system-level process terminations (`SIGKILL`, `sys.exit`) resolve to structured telemetry records rather than hanging the parent orchestration runtime.
