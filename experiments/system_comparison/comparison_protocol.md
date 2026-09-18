# Comparative Evaluation Protocol

This protocol establishes the scientific methodology governing comparisons between **RetailOps** and related published orchestration systems.

---

## 1. Classification of Comparisons

All comparative assertions in the RetailOps research paper must adhere to the following taxonomy:

1. **Direct Empirical Experiments (RetailOps Internal):**
   - Controlled paired benchmarks comparing the **RetailOps MCP Architecture** against the **Tightly Coupled Baseline**.
   - Identical domain algorithms, identical datasets, identical operating environment, and identical execution runs.
   - High statistical validity; isolated system variables.
2. **Literature-Based Architectural Comparisons (External Systems):**
   - Analysis comparing RetailOps with external systems (**Flowr**, **WorkflowLLM**, **Agentic Replenishment**) based on peer-reviewed papers and official preprints.
   - Qualitative and structural analysis; identifies architectural trade-offs, design patterns, and research scopes.
   - Strictly prohibits cross-paper quantitative rankings or competitive benchmarking.

---

## 2. Incomparability of External Published Metrics

Direct quantitative comparison of runtime latency, throughput, or accuracy across RetailOps and external published systems is scientifically invalid due to fundamental disparities in:

* **Workloads and Tasks:** Flowr evaluates live supermarket enterprise purchase orders; WorkflowLLM benchmarks NLP tool-use across synthetic datasets; Syed et al. evaluate continuous replenishment in a retail mart; RetailOps benchmarks sequential 5-stage retail pipelines.
* **Hardware and Deployment Environments:** Flowr and WorkflowLLM utilize GPU clusters for fine-tuned LLM inference; RetailOps benchmarks systems-level IPC on standard OS environments.
* **Measurement Protocols:** Flowr measures business compliance accuracy; WorkflowLLM measures API selection F1 score; RetailOps measures wall-clock process lifecycle and IPC latency in milliseconds.

> [!WARNING]
> Under no circumstances may published latency numbers from WorkflowLLM or operational percentages from Flowr be placed into a direct numerical comparison table with RetailOps benchmark numbers.

---

## 3. Evidence and Attribution Rules

1. **Primary Source Grounding:** Every claim regarding external systems must cite verified text from the primary paper (e.g. arXiv identifier, conference proceedings).
2. **No Negative Proofs:** The absence of a documented feature in an external paper must never be recorded as proof that the system lacks that feature. Use standard uncertainty labels:
   - *"Not reported in the reviewed source"*
   - *"Not established from the reviewed source"*
3. **Inference Tagging:** Any conceptual interpretation or extrapolation must be explicitly tagged as `evidence_type: inference` and distinguished from documented facts.
4. **No Fabricated Benchmarks:** No synthetic numbers, estimated latencies, or assumed costs may be assigned to external systems.
5. **Separation of Architectural Properties from Decision Quality:** Architectural modularity, service decoupling, and fault isolation must be evaluated separately from whether an underlying machine learning model generates accurate retail forecasts or pricing strategies.
