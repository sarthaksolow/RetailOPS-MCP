# Task 07: Fault Tolerance and Failure-Recovery Evaluation

## Overview

Task 07 evaluates the fault tolerance, error isolation, partial-result preservation, and downstream-stage protection of the **RetailOps** enterprise orchestration framework. RetailOps coordinates four distinct MCP services through STDIO transport:
1. **Catalog Enricher**: Resolves product titles and taxonomies.
2. **Forecasting**: Computes 30-day statistical demand projections.
3. **Replenishment Decision**: Evaluates inventory positions against forecasts to compute reorder quantities.
4. **Pricing Strategy**: Formulates dynamic price adjustments based on demand, inventory levels, and margin goals.

This experiment investigates how failures injected into individual stages propagate through the orchestration graph, whether completed stage outputs are reliably preserved, whether downstream services are shielded from executing against corrupted or missing dependencies, and whether subprocess sessions clean up without hanging.

---

## Experimental Design & Evaluated Scenarios

Fault injection is performed deterministically through controlled test hooks without altering production orchestration logic. Six scenarios are evaluated across both process-per-call and persistent session architectures:

| Scenario | Target Service | Failure Mode | Architectural Layer | Description |
|---|---|---|---|---|
| **Scenario A** | Catalog Enricher | `tool_error` | Process-per-Call | Catalog Enricher tool raises an exception; workflow flags error, attempts fallback category `general`, halts downstream replenishment and pricing cleanly. |
| **Scenario B** | Forecasting | `tool_error` | Process-per-Call | Forecasting service raises an exception; Catalog enrichment outputs are preserved; downstream Replenishment and Pricing nodes are protected from executing on invalid demand data. |
| **Scenario C** | Replenishment | `tool_error` | Process-per-Call | Replenishment tool raises an exception; Catalog and Forecast outputs are preserved; Pricing node is prevented from operating on incomplete inventory decisions. |
| **Scenario D** | Pricing Strategy | `tool_error` | Process-per-Call | Terminal Pricing tool fails; Enrichment, Forecast, and Replenishment partial results remain intact. |
| **Scenario E** | Replenishment | `tool_error` | Persistent Session Pool | Replenishment tool fails over a long-lived persistent MCP session; connection state remains healthy, subsequent requests succeed without session pollution, and sessions terminate cleanly. |
| **Scenario F** | Forecasting | `crash_exit` | Process-per-Call | Forecasting server process terminates abruptly via unhandled exit (`os._exit(1)`); client catches pipe termination, logs subprocess termination, avoids hang, and records failure status. |

---

## Benchmark Execution

To execute the automated benchmark suite with 10 repetitions per scenario (60 total workflow executions):

```bash
python experiments/fault_tolerance/benchmark.py --repetitions 10
```

Benchmark output files are generated in `experiments/fault_tolerance/`:
- `raw_results.jsonl`: Line-delimited JSON recording run metadata, execution latency, error classification, completed/failed steps, and evaluation status for each repetition.
- `summary.json`: Aggregated metrics including detection rates, expected behavior rates, partial preservation rates, downstream protection rates, cleanup success rates, and latency statistics.

---

## Unit and Contract Tests

The fault tolerance test suite evaluates all 12 functional criteria across error handling, downstream protection, session recovery, and taxonomy classification:

```bash
python test_fault_tolerance.py
```

### Full Regression Battery

```bash
python test_persistent_mcp.py
python test_performance_benchmark.py
python test_instrumentation.py
python test_baseline_comparison.py
python test_service_replacement.py
python test_integration.py
```
