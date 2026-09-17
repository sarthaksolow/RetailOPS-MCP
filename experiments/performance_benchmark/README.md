# Controlled Performance Benchmark: MCP vs Tightly Coupled Baseline

## 1. Overview
This benchmark measures and compares the execution latency and architectural runtime behavior between:
1. **Direct Tightly Coupled Baseline** (`baseline/tightly_coupled.py`): In-process Python function calls with zero inter-process communication.
2. **MCP-Based Architecture (Deterministic Local)**: LangGraph orchestrator invoking FastMCP servers via `stdio` using deterministic local logic (mock FastMCP servers for enricher, replenishment, pricing, plus the deterministic moving-average forecasting server).
3. **MCP-Based Architecture (End-to-End Production)**: Full production MCP pipeline with remote OpenRouter LLM inference across all four service stages.

---

## 2. Experimental Setup

### Hardware & Environment
- **OS**: Windows NT (`win32`)
- **Python Version**: 3.12.0
- **Orchestration**: LangGraph StateGraph (4 sequential nodes)
- **Transport**: STDIO pipes via FastMCP / MCP Python SDK
- **Warm-up**: 2 unmeasured warmup iterations prior to measured runs
- **Measured Iterations**:
  - Condition A (Deterministic Local): 30 iterations for Tightly Coupled, 30 iterations for MCP Architecture.
  - Condition B (End-to-End Production): 5 iterations for full production pipeline with live OpenRouter LLM calls.

### Timing Boundaries & Scope
- **Tightly Coupled Timing**: Captures end-to-end execution of `execute_workflow()`, plus exact per-stage execution durations recorded via high-resolution monotonic clocks (`time.perf_counter()`).
- **Deterministic MCP Timing**: Measures the full orchestrator node execution for each stage. Because the current orchestrator connects to FastMCP servers per node using `stdio_client`, each node invocation encompasses:
  1. Subprocess spawning (`python.exe <server_script>`)
  2. Python interpreter bootstrap and FastMCP initialization
  3. Client-server handshake and tool discovery (`ListToolsRequest`)
  4. Tool invocation (`CallToolRequest`), serialization/deserialization over stdin/stdout
  5. Deterministic service calculation
  6. Subprocess teardown
- **Important Distinction**: The runtime difference between Condition A (MCP) and Tightly Coupled represents the **end-to-end architectural runtime difference under per-node stdio subprocess lifecycle**, **NOT** isolated wire-protocol serialization overhead.

---

## 3. How to Run

Run the benchmark with default configuration (30 iterations, 2 warmups):
```powershell
python experiments/performance_benchmark/benchmark.py --iterations 30 --warmup 2
```

Run only deterministic benchmark (skipping external API calls):
```powershell
python experiments/performance_benchmark/benchmark.py --iterations 30 --warmup 2 --skip-e2e
```

Run automated validation tests:
```powershell
python test_performance_benchmark.py
```

---

## 4. Artifacts Produced
- `experiments/performance_benchmark/benchmark.py`: Benchmark runner script.
- `experiments/performance_benchmark/raw_results.jsonl`: Raw iteration records with timestamps, durations, service timings, status, and payload snapshots.
- `experiments/performance_benchmark/summary.json`: Aggregated statistics (mean, median, min, max, std dev, p95, completion rate) for all conditions.
- `experiments/performance_benchmark/results.md`: Complete empirical report and architectural discussion.
