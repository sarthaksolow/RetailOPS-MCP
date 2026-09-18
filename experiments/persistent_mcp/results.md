# Empirical Results: Persistent MCP Server and Process-Lifecycle Overhead Analysis

## 1. Executive Summary
This experiment evaluates how reusing persistent MCP server processes affects orchestration latency and isolates process-lifecycle overhead from inter-process communication overhead.

Across 90 measured executions (30 per architecture) following 10 warmup runs each:
- **Condition A (Tightly Coupled Baseline)** completed in a mean of **0.94 ms** (P95: 1.60 ms).
- **Condition B (MCP Process-per-Call)** completed in a mean of **11,489.28 ms** (P95: 13,314.00 ms).
- **Condition C (Persistent MCP Process)** completed in a mean of **37.75 ms** (P95: 41.93 ms).

All 90 measured executions completed with a **100.0% completion rate** and zero errors.

---

## 2. Quantitative Summary

### Overall Workflow Runtime Comparison

| Architecture | Measured Runs | Completion Rate | Mean Latency | Median Latency | Min Latency | Max Latency | Std Dev | P95 Latency |
|---|---|---|---|---|---|---|---|---|
| **Tightly Coupled Baseline** | 30 | 100.0% | **0.94 ms** | 0.89 ms | 0.58 ms | 2.14 ms | 0.32 ms | **1.60 ms** |
| **MCP Process-per-Call** | 30 | 100.0% | **11,489.28 ms** | 11,230.43 ms | 10,759.86 ms | 14,810.15 ms | 858.81 ms | **13,314.00 ms** |
| **Persistent MCP Process** | 30 | 100.0% | **37.75 ms** | 37.67 ms | 34.19 ms | 44.20 ms | 2.24 ms | **41.93 ms** |

---

## 3. Per-Service Latency Breakdown

### Mean and P95 Durations per Pipeline Stage

| Pipeline Stage | Tightly Coupled Mean (P95) | MCP Process-per-Call Mean (P95) | Persistent MCP Mean (P95) |
|---|---|---|---|
| **Catalog Enricher** | 0.03 ms (0.04 ms) | 2,725.14 ms (3,506.10 ms) | 9.80 ms (11.45 ms) |
| **Forecasting** | 0.80 ms (1.32 ms) | 1,911.60 ms (2,357.47 ms) | 7.42 ms (8.92 ms) |
| **Replenishment** | 0.02 ms (0.02 ms) | 2,698.15 ms (3,693.74 ms) | 9.94 ms (12.44 ms) |
| **Pricing Strategy** | 0.02 ms (0.05 ms) | 2,712.00 ms (3,016.17 ms) | 10.24 ms (12.49 ms) |
| **Total Pipeline** | **0.94 ms** (**1.60 ms**) | **11,489.28 ms** (**13,314.00 ms**) | **37.75 ms** (**41.93 ms**) |

---

## 4. Directly Measured Timing Boundaries & Lifecycle Breakdown

The `PersistentMCPSessionPool` instrumentation measured process startup and session initialization for each server during pool startup:

| Server Component | Process Spawn & Pipe Open | Session Context Enter | Session Initialize Handshake | Total Server Startup |
|---|---|---|---|---|
| **Catalog Enricher** | 7.67 ms | 0.04 ms | 2,530.38 ms | 2,538.10 ms |
| **Forecasting** | 6.59 ms | 0.03 ms | 1,781.09 ms | 1,787.70 ms |
| **Replenishment** | 6.96 ms | 0.03 ms | 2,548.98 ms | 2,555.98 ms |
| **Pricing Strategy** | 6.03 ms | 0.03 ms | 2,602.31 ms | 2,608.36 ms |
| **Total Pool Startup** | — | — | — | **9,490.23 ms** |

- **Subprocess & Session Shutdown**: All 4 subprocesses, stdin/stdout pipes, and AsyncExitStack handlers closed cleanly in **1,458.25 ms**.
- **Steady-State IPC Overhead**: Once the servers are initialized, executing a tool call over the persistent stdio session required only **7.42 ms to 10.24 ms** per stage.

---

## 5. Architectural Findings & Hypothesis Assessment

### 1. Does the overhead come from MCP communication or process lifecycle?
- **Finding**: Preliminary empirical evidence demonstrates that **over 99.6%** of the latency in the process-per-call architecture is due to repeatedly spawning, importing Python dependencies (`pydantic`, `mcp`, `fastmcp`), and running the JSON-RPC initialization handshake per node.
- Reusing persistent MCP server sessions reduced workflow execution latency from **11,489.28 ms** down to **37.75 ms**, representing a **304.35x speedup** (an absolute reduction of 11,451.53 ms per workflow execution).

### 2. Is MCP communication sub-millisecond?
- In-process baseline calls required **0.94 ms** total (~0.02 ms per stage).
- Persistent MCP tool calls required **37.75 ms** total (~7.4 to 10.2 ms per stage).
- While stdio JSON-RPC IPC is drastically faster than launching fresh subprocesses, individual tool calls in this environment averaged **~7–10 ms** each (including pipe I/O, event loop context switching, and JSON serialization). Thus, claims that MCP communication is sub-millisecond are not supported under this configuration.

### 3. Persistent-Session Feasibility in Production
- The official Python `mcp` SDK (`ClientSession` and `stdio_client`) successfully supports persistent multi-call sessions via asynchronous context managers (`AsyncExitStack`).
- Multiple sequential calls across independent workflows execute cleanly without state leakage when state is encapsulated per workflow execution.

---

## 6. Threats to Validity & Benchmark Limitations
1. **Operating System Subprocess Overhead**: This benchmark was conducted on Windows NT (`win32`). Windows process creation (`CreateProcess`) has higher latency than POSIX `fork`/`clone`. On Linux systems, process startup costs may be lower, though Python import times would remain non-trivial.
2. **Deterministic vs. Live LLM Latency**: Under production conditions where LLMs take 10–25 seconds per stage, the 11-second process lifecycle overhead represents ~10% of total runtime, whereas under deterministic local conditions it dominates total runtime.
3. **Transport Protocol**: This benchmark evaluated `stdio` transport. Alternative MCP transports (e.g., SSE / HTTP) may exhibit different connection reuse, serialization, and socket lifecycle characteristics.
4. **Server Failure Handling**: In a persistent model, if a server crashes mid-session, connection recovery mechanisms (e.g., automatic restart and session re-establishment) are required to avoid disrupting subsequent workflow invocations.

---

## 7. Research Implications & Recommended Next Steps
1. **Architectural Recommendation**: Production enterprise deployments of RetailOps should adopt persistent MCP server processes (or long-lived MCP daemon connections) rather than spawning processes per node.
2. **Next Steps**:
   - Evaluate resilient connection pooling with automatic process health checks and reconnection.
   - Investigate persistent SSE/HTTP transport for distributed multi-host deployments.
