# Task 08: Extensibility Evaluation of RetailOps

## Overview

This experiment evaluates the extensibility of the **RetailOps** decision orchestration framework by integrating a 5th specialized retail service: **Supplier Intelligence Service**.

We rigorously compare the integration effort, structural impact, and runtime behavior between:
1. **MCP-Based Architecture** (`servers/supplier-intelligence/server.py` + `client/extended_orchestrator.py`)
2. **Tightly Coupled In-Process Baseline** (`baseline/supplier_intelligence.py` + `baseline/extended_tightly_coupled.py`)

## Core Research Hypothesis

> **H1**: The MCP-based architecture can integrate an additional specialized service while limiting changes to existing service implementations and preserving existing service interfaces.

## Structure of the Experiment

1. **New Service**:
   - `servers/supplier-intelligence/server.py`: FastMCP server exposing `getSupplierIntelligence(category, reorder_qty)`.
   - `baseline/supplier_intelligence.py`: Direct Python implementation exposing `direct_get_supplier_intelligence(category, reorder_qty)`.

2. **Orchestration Pipelines**:
   - Original 4-stage pipeline: `enrich -> forecast -> replenish -> price`.
   - Extended 5-stage pipeline: `enrich -> forecast -> replenish -> supplier -> price`.

3. **Metrics Evaluated**:
   - **Structural Metrics**: Files created/modified, LOC created/modified, interface changes.
   - **Runtime Metrics**: Pipeline completion status, step completion sequence, vendor recommendations, latency.
   - **Architectural Isolation**: Process boundaries, transport protocol, fault isolation.

## Running the Evaluation

To execute the benchmark and generate updated metrics:
```bash
python experiments/extensibility/evaluate.py
```

To run the automated extensibility test suite:
```bash
python test_extensibility.py
```

## Generated Artifacts

- `raw_results.jsonl`: Line-delimited JSON records of each empirical run.
- `summary.json`: Aggregated structural metrics, latency statistics, and hypothesis findings.
- `results.md`: Complete research report and comparative analysis table.
