# Source Verification and Bibliographic Record

This document records the exact bibliographic metadata, verified text excerpts, access URLs, and evidence classifications for all references examined in this comparative study.

---

## 1. Primary External Literature

### 1.1 Flowr (Reference 4)

* **Full Title:** *Flowr -- Scaling Up Retail Supply Chain Operations Through Agentic AI in Large Scale Supermarket Chains*
* **Authors:** Eranga Bandara, Ross Gore, Sachin Shetty, P. Siyambalapitiya, S. Rajapakse, I. Kularathna, P. Karunarathna, R. Mukkamala, P. Foytik, S. H. Bouk, A. Rahman, X. Liang, A. Hass, T. Hewa, N. W. Keong, K. De Zoysa, A. Withanage, N. Loganathan
* **Year:** 2026 (Submitted April 7, 2026)
* **Venue / Publication:** arXiv preprint `arXiv:2604.05987` [cs.AI]
* **URL:** [https://arxiv.org/abs/2604.05987](https://arxiv.org/abs/2604.05987)
* **Verified Abstract & Text Excerpts:**
  > *"End-to-end supply chain operations in large-scale supermarket chains are traditionally manual, repetitive, and fragmented across isolated human workflows... We introduce Flowr, an agentic AI framework that decomposes these operations into specialized AI agents that handle specific cognitive tasks, including Demand Forecasting, Inventory Monitoring and Stockout Detection, Procurement and Purchase Order Generation, Supplier Coordination, Distribution Center Replenishment Planning, and Exception Handling."*
  > *"To ensure accuracy and reduce hallucinations, the system uses a consortium of fine-tuned, domain-specialized Large Language Models (LLMs) coordinated by a central reasoning LLM."*
  > *"Supply chain managers retain control and accountability through a Model Context Protocol (MCP)-enabled interface, allowing them to supervise and intervene in agent workflows as needed."*
  > *"The framework was validated in collaboration with a large-scale supermarket chain... demonstrating proactive management of supply chain exceptions at an enterprise scale."*
* **Verified Claims:**
  - Addresses supermarket supply chain workflows (forecasting, inventory, procurement, supplier coordination).
  - Uses specialized AI agents backed by a consortium of fine-tuned domain LLMs coordinated by a central reasoning LLM.
  - Implements human-in-the-loop supervision via an MCP-enabled interface.
  - Validated in an enterprise collaboration with a supermarket chain.
* **Claims Not Established / Excluded:**
  - Numerical compliance percentages (e.g. 95%) or zero false escalation counts are not established from the primary arXiv text and are excluded.
  - Proprietary asset ownership breakdown is not established and is excluded.
  - Service replacement and process-level crash cleanup experiments are not reported in the reviewed source.

---

### 1.2 WorkflowLLM (Reference 6)

* **Full Title:** *WorkflowLLM: Enhancing Workflow Orchestration Capability of Large Language Models*
* **Authors:** Shengda Fan, Xin Cong, Yuepeng Fu, Zhong Zhang, Shuyan Zhang, Yuanwei Liu, Yesai Wu, Yankai Lin, Zhiyuan Liu, Maosong Sun
* **Affiliations:** Renmin University of China, Tsinghua University, ModelBest Inc.
* **Year:** 2025 (Presented at ICLR 2025, arXiv submitted November 2024)
* **Venue / Publication:** *International Conference on Learning Representations (ICLR 2025)*, arXiv preprint `arXiv:2411.02052` [cs.CL]
* **URL:** [https://arxiv.org/abs/2411.02052](https://arxiv.org/abs/2411.02052) | [OpenReview](https://openreview.net/forum?id=V8vF0HqDq7) | [GitHub Repository](https://github.com/OpenBMB/WorkflowLLM)
* **Verified Abstract & Text Excerpts:**
  > *"Workflow orchestration is a critical component of Agentic Process Automation, requiring models to dynamically create, execute, and adapt multi-step tool-use workflows."*
  > *"We construct WorkflowBench, a large-scale workflow orchestration dataset containing 106,763 synthesis and execution samples covering 1,503 APIs across 83 applications and 28 categories."*
  > *"We train WorkflowLlama (fine-tuned on Llama-3.1-8B) to generate and adapt workflows dynamically from user intents, evaluating on both in-distribution and out-of-distribution benchmark suites (e.g., T-Eval)."*
* **Verified Claims:**
  - Evaluates automated generation and execution of multi-step tool workflows by fine-tuned LLMs.
  - Introduces WorkflowBench (106,763 samples, 1,503 APIs) and WorkflowLlama model.
  - Focuses on generalized API orchestration, dynamic planning, and tool selection.
* **Claims Not Established / Excluded:**
  - Not designed specifically for retail decision pipelines or supermarket operations.
  - Does not use Model Context Protocol (MCP) or LangGraph.
  - Does not evaluate OS subprocess lifecycles, IPC overhead, or process cleanup.

---

### 1.3 Agentic AI Framework for Smart Inventory Replenishment (Reference 9)

* **Full Title:** *Agentic AI Framework for Smart Inventory Replenishment*
* **Authors:** Toqeer Ali Syed, Salman Jan, Gohar Ali, Ali Akarma, Ahmad Ali, Qurat-ul-Ain Mastoi
* **Affiliations:** Department of Computer Science, National University of Computer and Emerging Sciences; University of Engineering and Technology; Universiti Teknologi PETRONAS
* **Year:** 2025 (Submitted November 28, 2025)
* **Venue / Publication:** Presented at the *International Conference on Business and Digital Technology (ICBDT 2025)* in Bahrain (Springer Nature); arXiv preprint `arXiv:2511.23366` [cs.AI]
* **URL:** [https://arxiv.org/abs/2511.23366](https://arxiv.org/abs/2511.23366)
* **Verified Abstract & Text Excerpts:**
  > *"Traditional replenishment methods like EOQ and ROP struggle with thousands of SKUs, volatile demand, and complex supplier relationships... We propose an Agentic AI framework—autonomous agents capable of perceiving, reasoning, negotiating, and acting—combining LLMs and reinforcement learning for retail inventory replenishment."*
  > *"The system monitors inventory levels, initiates purchase orders, selects optimal suppliers, and scans for high-margin or trending products."*
  > *"Tested in a middle-scale mart setting against conventional heuristics, showing decreased stockouts, reduced holding costs, and improved inventory turnover."*
* **Verified Claims:**
  - Focuses specifically on retail inventory replenishment and supplier order negotiation.
  - Uses autonomous multi-agent reasoning combining LLMs and reinforcement learning.
  - Evaluated in a middle-scale mart setting measuring operational retail KPIs (stockout rates, holding costs, turnover).
* **Claims Not Established / Excluded:**
  - Does not utilize MCP or standardized tool protocols for inter-service communication.
  - Does not evaluate systems-level software engineering metrics (LOC churn, IPC latency, process fault isolation).
  - Source code and reproducible datasets were not established from the reviewed preprint.

---

## 2. RetailOps Implementation & Empirical Evidence

### 2.1 Repository Context
* **Repository:** `RetailOps: An MCP-Based Enterprise Decision Orchestration Framework for Autonomous Retail Operations`
* **Active Branch:** `phase-2-client-orchestrator`
* **Core Source Artifacts:**
  - `client/orchestrator.py`: LangGraph `StateGraph` sequential pipeline coordinating 4 microservices.
  - `client/extended_orchestrator.py`: Extended 5-stage pipeline incorporating Supplier Intelligence.
  - `servers/`: FastMCP STDIO servers (`catalog-enricher`, `forecasting`, `forecasting-replacement`, `replenishment`, `pricing-strategy`, `supplier-intelligence`).
  - `baseline/`: Paired in-process Python baseline implementations (`tightly_coupled.py`, `extended_tightly_coupled.py`).
  - `client/mcp_pool.py`: Persistent session manager pooling FastMCP processes across workflow executions.

### 2.2 Verified Empirical Results (Tasks 04–08)
* **Task 04 (Service Replacement):**
  - Location: `experiments/service_replacement/summary.json`
  - Result: Forecasting service replaced with 60-day moving average variant with 0 modifications to existing services and 100% downstream decision consumption.
* **Task 05 (Deterministic Runtime Benchmark):**
  - Location: `experiments/runtime_benchmark/deterministic_summary.json`
  - Result: Measured paired latency distributions across 30 runs; baseline mean 0.81 ms vs. process-per-call MCP mean 10,891.45 ms on Windows.
* **Task 06 (Persistent MCP Session Lifecycle):**
  - Location: `experiments/persistent_mcp/summary.json`
  - Result: Persistent MCP session pooling amortized workflow latency to mean 37.75 ms (startup 9,490.23 ms, shutdown 1,458.25 ms across 30 runs) compared to 11,489.28 ms for process-per-call.
* **Task 07 (Fault Tolerance & Cleanup):**
  - Location: `experiments/fault_tolerance/summary.json`
  - Result: 60 fault injection runs across 6 failure modes (tool errors, crash exits, invalid schemas). 100% failure detection, 100% downstream protection abort via `failed_enrichment`, and 0 zombie processes verified via `psutil`.
* **Task 08 (Extensibility):**
  - Location: `experiments/extensibility/summary.json`
  - Result: 5th service (Supplier Intelligence) added with 0 existing service files modified, 0 existing LOC modified, 183 LOC new service, and 100% domain output parity across 11 fields.
