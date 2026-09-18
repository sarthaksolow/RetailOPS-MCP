# Task 09: System Comparison and Evaluation Framework

This directory contains research-paper-ready, source-grounded comparative analyses and evaluation frameworks for **RetailOps** against three published state-of-the-art agentic orchestration frameworks:

1. **Flowr** (Bandara et al., 2026, [arXiv:2604.05987](https://arxiv.org/abs/2604.05987)): Multi-agent retail supply chain operations for supermarket chains with central reasoning and MCP integration.
2. **WorkflowLLM** (Fan et al., ICLR 2025, [arXiv:2411.02052](https://arxiv.org/abs/2411.02052)): Data-centric framework fine-tuning LLMs (WorkflowLlama) for workflow orchestration and generation across multi-tool APIs.
3. **Agentic AI Framework for Smart Inventory Replenishment** (Syed et al., 2025, [arXiv:2511.23366](https://arxiv.org/abs/2511.23366)): Autonomous multi-agent retail replenishment system with LLM perception, negotiation, and reinforcement learning.

## Methodological Guidelines

In accordance with strict academic standards:
- **No Claims of Universal Superiority**: RetailOps is not claimed to be "better", "superior", or declared as the single prevailing architecture. The analysis evaluates architectural characteristics, trade-offs, and empirical systems-engineering boundaries.
- **Strict Evidence Classification**: Every claim is tagged as `literature`, `implementation`, `experiment`, or `inference`.
- **Negative Proof Avoidance**: Features not reported in external publications are marked as *"Not reported in the reviewed source"* or *"Not established from the reviewed source"*, never as missing or non-existent.
- **Model Quality vs. Orchestration Separation**: Model forecasting/pricing accuracy is evaluated separately from systems orchestration metrics (IPC overhead, process cleanup, extensibility LOC).

## Artifact Directory Structure

- [`source_verification.md`](source_verification.md): Exact bibliographic metadata, verified text excerpts, and evidence tracking for all references.
- [`system_comparison_matrix.md`](system_comparison_matrix.md): Comprehensive Markdown comparison matrix covering all required dimensions with evidence status.
- [`comparison_analysis.md`](comparison_analysis.md): Academic research narrative detailing architectural similarities, differences, research gaps, and RetailOps implications.
- [`comparison_protocol.md`](comparison_protocol.md): Methodological protocol governing direct experiments vs. literature analyses.
- [`evaluation_framework.md`](evaluation_framework.md): Formal definitions of 6 metric groups (Integration Effort, Extensibility, Service Replacement, Execution Performance, Reliability, and AI Capability).
- [`system_scope_table.md`](system_scope_table.md): Research Table 1 (System Scope Comparison).
- [`architecture_comparison_table.md`](architecture_comparison_table.md): Research Table 2 (Architecture Comparison).
- [`evaluation_methodology_table.md`](evaluation_methodology_table.md): Research Table 3 (Evaluation Methodology Comparison).
- [`retailops_evaluation_mapping.md`](retailops_evaluation_mapping.md): Research Table 4 (RetailOps Evaluation Mapping).
- [`evidence_registry.json`](evidence_registry.json): Machine-readable registry of verified claims with confidence and source locations.
- [`results_summary.json`](results_summary.json): Empirical measurements from RetailOps Tasks 04–08.
