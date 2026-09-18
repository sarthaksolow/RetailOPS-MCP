# Persistent MCP Server and Process-Lifecycle Overhead Analysis

## 1. Overview
This experiment investigates the research question:
> **How does reusing persistent MCP server processes affect execution latency and process-lifecycle overhead compared with launching a new MCP process for every service invocation?**

The primary objective is to determine whether the ~9.5 to ~11.5 second deterministic execution overhead observed in Task 05 stems primarily from MCP communication itself (JSON-RPC over stdio) or from repeatedly spawning, importing, and initializing Python processes per service call.

---

## 2. Experimental Design

### Architectures Evaluated
The benchmark compares three architectures on identical deterministic workloads with zero external API calls:

1. **Condition A: Tightly Coupled Baseline**
   - In-process direct Python function calls.
   - Zero IPC, zero subprocesses.
2. **Condition B: MCP Process-per-Call**
   - Standard LangGraph orchestrator launching servers via `stdio_client` per node.
   - Spawns 4 independent Python subprocesses per workflow execution.
3. **Condition C: Persistent MCP Process**
   - `PersistentMCPSessionPool` starting 4 FastMCP servers once at workflow initialization.
   - Reuses the existing client sessions and stdio streams across multiple workflow iterations.
   - Cleanly terminates sessions and subprocesses at benchmark exit.

### Timing Boundaries & Metrics
- **Directly Measured Metrics**:
  - Process spawn and pipe creation latency.
  - Client-session initialization handshake latency (`session.initialize()`).
  - Tool invocation latency over persistent stdio streams (`session.call_tool()`).
  - Total workflow duration per execution via high-resolution monotonic clocks (`time.perf_counter()`).
  - Pool shutdown and process cleanup duration.
- **Derived Metrics**:
  - Absolute latency differences between architectures.
  - Speedup factor achieved by eliminating per-node process lifecycles.
- **Experimental Controls**:
  - 10 warmup runs per architecture.
  - 30 measured runs per architecture (90 total measured runs).
  - Identical catalog items (`Samsung TV`, `Dell XPS Laptop`, `Apple iPhone 15`).

---

## 3. How to Run

Execute the benchmark suite:
```powershell
python experiments/persistent_mcp/benchmark.py --iterations 30 --warmup 10
```

Execute the validation unit tests:
```powershell
python test_persistent_mcp.py
```

---

## 4. Artifacts
- `experiments/persistent_mcp/benchmark.py`: Benchmark runner for Conditions A, B, and C.
- `experiments/persistent_mcp/raw_results.jsonl`: 90 measured records + 30 warmup records.
- `experiments/persistent_mcp/summary.json`: Descriptive statistics and lifecycle breakdown.
- `experiments/persistent_mcp/results.md`: Empirical report, lifecycle observations, and research implications.
