# RetailOps Formal Evaluation Framework

## Overview

The `experiments/evaluation_framework/` directory establishes a standardized, reproducible, and academically defensible evaluation framework for the **RetailOps** project.

This framework enables consistent measurement of multi-agent and microservice orchestration systems across six core engineering and scientific dimensions:
1. **Integration Effort** (Code churn, interface stability, cross-service dependencies)
2. **Extensibility** (Isolation, regression safety, schema compatibility)
3. **Service Replacement** (Upstream/downstream blast radius, schema adherence)
4. **Performance & Overhead** (Process spawn, session handshake, pure IPC latency, persistent amortization)
5. **Reliability & Fault Handling** (Failure detection, partial result preservation, downstream protection, process cleanup)
6. **Model Quality Scope Separation** (Clear demarcation between orchestration engineering metrics and domain algorithm accuracy)

## Directory Structure

* [`metrics_schema.json`](file:///E:/Repositories/RetailOPS-MCP/experiments/evaluation_framework/metrics_schema.json): Formal JSON Schema (Draft 2020-12) specifying required fields, allowed enums, and data types for all benchmark summaries.
* [`evaluation_protocol.md`](file:///E:/Repositories/RetailOPS-MCP/experiments/evaluation_framework/evaluation_protocol.md): Methodological guidelines, terminology standards, and reproducibility checklists.
* [`experiment_matrix.json`](file:///E:/Repositories/RetailOPS-MCP/experiments/evaluation_framework/experiment_matrix.json): Comprehensive matrix mapping six core research questions to their respective baselines, implementations, metrics, and empirical findings.

## Evidence Hierarchy

To maintain scientific integrity, all evaluations must categorize claims into three evidence tiers:
* `literature`: Established from published peer-reviewed or preprint papers and technical documentation.
* `implementation`: Verifiable directly in the repository source code and structural static analysis.
* `experiment`: Supported by executed test harnesses, raw JSONL telemetry, and statistical distributions.
