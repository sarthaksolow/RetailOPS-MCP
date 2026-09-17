# Empirical Results: Runtime and Orchestration Overhead Benchmark

## 1. Executive Summary
This experiment isolates and evaluates the runtime characteristics of the MCP-based RetailOps orchestration architecture against the in-memory tightly coupled baseline.

To avoid confounding architecture overhead with external network and LLM inference delays, the benchmark evaluated both:
1. **Condition A (Deterministic Local)**: 30 measured runs comparing in-process direct Python functions vs. local deterministic FastMCP servers running over stdio.
2. **Condition B (End-to-End Production)**: 5 measured runs of the full production MCP pipeline communicating with OpenRouter LLMs.

All 65 measured executions completed with a **100% success rate** and zero failures.

---

## 2. Quantitative Summary

### Overall Workflow Runtime Comparison (Condition A & B)

| Metric | Tightly Coupled (Det) | MCP Architecture (Det) | MCP Architecture (End-to-End) |
|---|---|---|---|
| **Sample Size (N)** | 30 | 30 | 5 |
| **Completion Rate** | 100.0% (30/30) | 100.0% (30/30) | 100.0% (5/5) |
| **Mean Runtime** | 3.50 ms | 9,586.15 ms (~9.59 s) | 100,034.82 ms (~100.03 s) |
| **Median Runtime** | 2.50 ms | 9,430.13 ms (~9.43 s) | 90,292.51 ms (~90.29 s) |
| **Min Runtime** | 2.28 ms | 9,052.02 ms (~9.05 s) | 74,440.10 ms (~74.44 s) |
| **Max Runtime** | 28.37 ms | 11,102.17 ms (~11.10 s) | 125,134.88 ms (~125.13 s) |
| **Std Deviation** | 4.72 ms | 458.05 ms | 22,368.61 ms |
| **95th Percentile (P95)** | 4.14 ms | 10,309.89 ms (~10.31 s) | 125,134.88 ms (~125.13 s) |

---

## 3. Per-Service Breakdown

### Condition A: Deterministic Local Comparison

| Stage | Tightly Coupled Mean (P95) | MCP Deterministic Mean (P95) | Mean Difference |
|---|---|---|---|
| **Catalog Enricher** | 0.01 ms (0.02 ms) | 2,273.16 ms (2,525.86 ms) | +2,273.15 ms |
| **Forecasting** | 0.40 ms (0.53 ms) | 1,645.37 ms (1,975.52 ms) | +1,644.97 ms |
| **Replenishment** | 0.01 ms (0.01 ms) | 2,265.13 ms (2,671.50 ms) | +2,265.12 ms |
| **Pricing Strategy** | 0.01 ms (0.01 ms) | 2,297.73 ms (2,564.24 ms) | +2,297.72 ms |
| **Total Pipeline** | **3.50 ms** (**4.14 ms**) | **9,586.15 ms** (**10,309.89 ms**) | **+9,582.65 ms** |

### Condition B: End-to-End Production (with OpenRouter LLMs)

| Stage | Mean Runtime | Median Runtime | P95 Runtime | Std Dev |
|---|---|---|---|---|
| **Catalog Enricher** | 46,392.93 ms (~46.39 s) | 40,694.95 ms | 74,742.37 ms | 17,901.16 ms |
| **Forecasting** | 22,481.62 ms (~22.48 s) | 19,824.22 ms | 40,566.57 ms | 10,396.87 ms |
| **Replenishment** | 13,409.27 ms (~13.41 s) | 13,717.58 ms | 14,548.45 ms | 1,133.51 ms |
| **Pricing Strategy** | 15,158.37 ms (~15.16 s) | 15,358.79 ms | 16,408.78 ms | 1,296.59 ms |
| **Total Pipeline** | **100,034.82 ms** (~100.03 s) | **90,292.51 ms** | **125,134.88 ms** | **22,368.61 ms** |

---

## 4. Architectural Findings & Breakdown of Overhead

### Subprocess Lifecycle vs. Protocol Overhead
In the current implementation of RetailOps:
1. The LangGraph orchestrator opens a new FastMCP server session via `stdio_client` inside each node function (`enrich_node`, `forecast_node`, `replenishment_node`, `pricing_node`).
2. On Windows NT, spawning a new Python subprocess requires ~1.5 to 2.2 seconds per process (loading libraries such as `pydantic`, `mcp`, `fastmcp`, `anyio`).
3. Multiplying across 4 sequential stages yields approximately ~8.0 to 9.5 seconds of baseline process lifecycle overhead.
4. **Clarification**: The measured ~9.58 second deterministic runtime for MCP is **not pure MCP wire-protocol serialization overhead**. Pure JSON-RPC serialization over pipes takes sub-millisecond durations; the dominant cost in this architecture is the repeated subprocess instantiation and interpreter boot per node.
5. In contrast, the tightly coupled baseline executes in-process on the same interpreter thread, requiring only **~3.5 ms** total.

### External Service Latency vs. Architecture Overhead
1. Under production settings (Condition B), end-to-end execution took an average of **100,034.82 ms (~100 seconds)**.
2. In this operational mode:
   - External LLM generation and network latency account for **~90.4%** of total execution time (~90.4 seconds).
   - Architectural and process lifecycle overhead (~9.58 seconds) accounts for **~9.6%** of total runtime.
3. For enterprise batch workloads where individual LLM reasoning cycles take tens of seconds, a ~9-second process isolation cost represents a modest fraction of total latency; however, for interactive or sub-second operational queries, per-node subprocess launching is prohibitive.

---

## 5. Threats to Validity and Benchmark Limitations
1. **Per-Node Subprocess Connection**: The benchmark measures the orchestrator's current behavior where servers are spawned and torn down per node. A persistent daemon pool (or long-lived MCP client connection) would eliminate the subprocess boot cost and significantly reduce Condition A latency.
2. **Operating System Subprocess Performance**: Windows process creation (`CreateProcess`) has noticeably higher latency compared to POSIX `fork()`/`clone()`. On Linux, Python subprocess initialization is typically 2x to 4x faster.
3. **LLM Non-Determinism in Condition B**: Token output length and OpenRouter server queue delays vary significantly run-to-run (standard deviation of 22.3 seconds across 5 runs), illustrating why Condition A was necessary to evaluate architecture latency independently.
4. **Input Diversity**: The benchmark cycled through 3 representative product items across the retail electronics catalog (`Apple iPhone 15`, `Samsung TV`, `Dell XPS Laptop`).
