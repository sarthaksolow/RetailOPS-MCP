# System Comparison Matrix: RetailOps vs. Related Systems

This matrix compares **RetailOps** with three representative published systems from the literature:
1. **Flowr** (Bandara et al., 2026, [arXiv:2604.05987](https://arxiv.org/abs/2604.05987))
2. **WorkflowLLM** (Fan et al., ICLR 2025, [arXiv:2411.02052](https://arxiv.org/abs/2411.02052))
3. **Agentic Inventory Replenishment** (Syed et al., 2025, [arXiv:2511.23366](https://arxiv.org/abs/2511.23366))

---

## Comprehensive Multi-System Comparison Matrix

| Dimension | RetailOps | Flowr | WorkflowLLM | Agentic Inventory Replenishment | Evidence status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary Domain** | Autonomous retail decision pipeline (enrichment, forecasting, replenishment, supplier intelligence, pricing) | Supermarket supply chain operations (forecasting, inventory, procurement, DC replenishment, logistics) | General-purpose multi-application workflow orchestration across public APIs | Retail inventory replenishment, supplier order generation, and SKU mix optimization | Documented in literature & implementation |
| **Workflow Scope** | Sequential 5-stage decision pipeline | End-to-end multi-echelon supermarket supply chain | Multi-step user-intent task automation across 83 software applications | Replenishment ordering, stock monitoring, and supplier negotiation | Documented in literature & implementation |
| **Agent / Service Structure** | Microservice-backed functional tools running as standalone Python executables | Network of specialized cognitive agents backed by domain-specialized LLMs | Unified fine-tuned LLM (WorkflowLlama) generating API call graphs | Multi-agent architecture combining LLMs with reinforcement learning agents | Documented in literature & implementation |
| **Orchestration Mechanism** | Explicit StateGraph DAG via LangGraph with state accumulation and node failure guards | Central reasoning LLM orchestrator coordinating a multi-agent consortium | LLM-driven generative planning creating dynamic workflow graphs from prompts | Multi-agent autonomous reasoning and negotiation loops | Documented in literature & implementation |
| **Workflow Behavior (Static vs. Dynamic)** | Static, deterministic DAG with explicit conditional branching guards | Dynamic planning and agent coordination coordinated by central LLM | Dynamic workflow generation and adaptive step execution | Dynamic multi-agent negotiation and state updates | Documented in literature & implementation |
| **Inter-Service / Tool Protocol** | Model Context Protocol (FastMCP) over STDIO JSON-RPC 2.0 with persistent session pooling | Model Context Protocol (MCP) used as an interface to databases, tools, and UI | Standard REST / JSON APIs integrated into fine-tuning dataset (WorkflowBench) | Custom internal agent messaging and simulation environment interfaces | Documented in literature & implementation |
| **Interface Standardization** | Standardized MCP tool schemas and JSON-RPC 2.0 message contracts | Standardized MCP interfaces connecting agents to enterprise systems | Standardized OpenAPI / REST tool signatures | Not reported in the reviewed source | Partially documented |
| **Service Decoupling** | Separate OS subprocesses with no shared memory or global state | Decentralized agent architecture with domain role decomposition | Integrated into LLM tool-calling prompt contexts | Decentralized agent roles | Verified in implementation / Documented in literature |
| **Service Extensibility** | Experimentally verified in Task 08: 5th service added with 0 LOC modified in existing services | Described as a domain-independent blueprint; quantitative extension effort not reported | Extensible via fine-tuning or few-shot in-context learning over new APIs | Not reported in the reviewed source | Verified experimentally / Partially documented |
| **Service Replacement** | Experimentally verified in Task 04: Forecasting replaced with 0 LOC modified in existing services | Modular agent replacement discussed conceptually, but empirical replacement experiments not reported | Model weights or API endpoints can be updated; replacement effort not explicitly evaluated | Not reported in the reviewed source | Verified experimentally / Not reported in literature |
| **Human Supervision** | Autonomous batch execution; formatted store-manager explanation narratives | Dedicated human-in-the-loop (HITL) supervisory interface enabled by MCP | Autonomous API execution without mandatory interactive human-in-the-loop gates | Autonomous ordering with human managerial oversight noted in deployment context | Documented in literature & implementation |
| **Reliability & Fault Handling** | Experimentally verified in Task 07 across 6 failure modes; 100% downstream protection and psutil cleanup | Pre-Action Governance Reasoning Loop (PAGRL) and policy exception handling reported | Execution error handling and dynamic re-planning evaluated on benchmark tasks | Heuristic constraint checking within reinforcement learning environment | Verified experimentally / Documented in literature |
| **Process Isolation & OS Boundaries** | Separate MCP service processes communicating through STDIO; verified process cleanup | Not established whether Flowr uses specific OS subprocess isolation mechanisms | In-process model generation or simulated benchmark execution environments | Not established whether specific OS subprocess isolation is used | Verified in implementation / Not established in literature |
| **Evaluation Focus** | Systems engineering: Latency, process overhead, code churn, fault injection, session pooling | Enterprise operational validation: Supply chain exception management and workflow coordination | Machine learning & NLP: Workflow generation accuracy, API selection, parameter accuracy | Operational retail KPIs: Stockout rates, holding costs, inventory turnover | Documented in literature & implementation |
| **Baseline Configuration** | Paired in-process Python baseline executing identical business logic without MCP | Not established from reviewed source | Standard foundation models (Llama-3.1, GPT-4) without workflow fine-tuning | Conventional inventory heuristics (EOQ, (s, S) Reorder Point policies) | Documented in literature & implementation |
| **Public Reproducibility** | Local repository prototype with deterministic test harnesses and raw JSONL telemetry | Published preprint (arXiv:2604.05987); full code and enterprise data not established from source | Open-source dataset (WorkflowBench) and code repository on GitHub | Published preprint (arXiv:2511.23366); standalone code repository not established from source | Documented in literature & implementation |
| **Hardware & Deployment Context** | Standard CPU / local OS testbed; zero specialized fine-tuned GPU requirements | Multi-model fine-tuned LLM cluster deployed with commercial supermarket infrastructure | GPU clusters for fine-tuning Llama-3.1-8B; benchmark evaluation harness | Local simulation environment and middle-scale retail mart deployment | Documented in literature & implementation |

---

## Evidence Status Legend

- **Verified in implementation**: Formally confirmed through inspection of the RetailOps source code, configuration files, or unit/integration test suites.
- **Verified experimentally**: Established via reproducible benchmark executions and raw JSONL telemetry logs in RetailOps (Tasks 04–08).
- **Documented in literature**: Explicitly stated and confirmed in peer-reviewed conference proceedings or official preprint papers.
- **Partially documented**: Mentioned conceptually or in part in the literature, without complete technical specifications.
- **Not reported in the reviewed source**: The reviewed publications do not provide information regarding this dimension.
- **Not established from the reviewed source**: Available sources are insufficient to determine whether the system incorporates this characteristic.
- **Not directly comparable**: Underlying workloads, task definitions, or experimental methodologies differ fundamentally.
