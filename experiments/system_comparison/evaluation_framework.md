# Evaluation Framework: Metric Groups and Measurement Definitions

To facilitate rigorous, reproducible systems research in enterprise AI orchestration, this document formalizes the **RetailOps Evaluation Framework**. It establishes six metric groups separating software engineering properties, runtime performance, reliability, and AI model quality.

---

## Group A: Integration Effort

Measures the engineering complexity and developer effort required to integrate a new specialized AI service into the orchestration architecture.

* **Metric A.1: Existing Service Files Modified ($F_{\text{mod}}$)**
  - *Definition:* Total count of existing service source code files modified to integrate the new component.
  - *Measurement:* Git diff / file tree inspection. In a fully decoupled architecture, $F_{\text{mod}} = 0$.
* **Metric A.2: Existing Service Lines of Code Modified ($\text{LOC}_{\text{mod}}$)**
  - *Definition:* Total number of added, deleted, or modified lines across existing service implementations.
  - *Measurement:* Computed via `git diff --stat` across service directories.
* **Metric A.3: Existing Service Function Signatures Modified ($S_{\text{mod}}$)**
  - *Definition:* Number of public function headers or class methods altered in existing services.
  - *Measurement:* AST inspection of service definitions.
* **Metric A.4: Orchestration Extension Code ($\text{LOC}_{\text{orch}}$)**
  - *Definition:* Lines of code added to the client orchestrator to register, route, and consume the new service.
  - *Measurement:* Line count of new orchestrator nodes, state schema additions, and edge transitions.

---

## Group B: Extensibility

Measures the architectural adaptability of the framework when incorporating new business stages or domain capabilities.

* **Metric B.1: Cross-Service Dependency Count ($D_{\text{cross}}$)**
  - *Definition:* Number of direct import statements, shared memory references, or global state variables linking one microservice to another.
  - *Measurement:* Static analysis of import graphs. Target: $D_{\text{cross}} = 0$.
* **Metric B.2: Protocol Schema Conformance**
  - *Definition:* Verification that the new service communicates strictly via standard JSON-RPC 2.0 schemas without bespoke IPC wrappers.
  - *Measurement:* JSON Schema validation of tool definitions and message envelopes.
* **Metric B.3: End-to-End State Accumulation Parity**
  - *Definition:* Verification that extending the pipeline preserves state consistency and produces field-by-field parity across baseline and protocol-mediated workflows.
  - *Measurement:* Automated field-by-field equality assertions across test runs.

---

## Group C: Service Replacement

Measures the blast radius and modification effort required to swap an existing service implementation with an alternative variant conforming to the same interface.

* **Metric C.1: Sibling Service Code Churn ($\text{LOC}_{\text{sib}}$)**
  - *Definition:* Lines of code modified in upstream or downstream services when a target service is replaced.
  - *Measurement:* `git diff` on untouched service directories. Target: $\text{LOC}_{\text{sib}} = 0$.
* **Metric C.2: Orchestrator Target Reconfiguration Effort**
  - *Definition:* Changes required in the client to point to the replacement service (e.g. changing an executable path vs. rewriting node logic).
  - *Measurement:* Parameter toggle count (e.g. `server_params` update).
* **Metric C.3: Downstream Decision Consumption Rate**
  - *Definition:* Percentage of downstream pipeline stages that successfully ingest the replacement service's output and complete their execution without failure.
  - *Measurement:* Automated test assertion across replacement runs.

---

## Group D: Execution Performance

Measures runtime latency and process lifecycle overhead under controlled experimental conditions. Runtime measurements must be decomposed into explicit lifecycle components.

* **Metric D.1: Process Initialization Latency ($T_{\text{init}}$)**
  - *Definition:* Time required to spawn the Python runtime, import dependencies, and complete the MCP initialization handshake.
  - *Measurement:* Timestamp delta from `subprocess.Popen` to `client.initialize()` acknowledgement.
* **Metric D.2: Warm-Call Execution Latency ($T_{\text{call}}$)**
  - *Definition:* Latency of an individual tool invocation over an already established, persistent MCP session.
  - *Measurement:* Timestamp delta from JSON-RPC `CallToolRequest` dispatch to `CallToolResult` reception.
* **Metric D.3: Total Workflow Latency ($T_{\text{wf}}$)**
  - *Definition:* Wall-clock time required for the entire multi-stage pipeline to execute from start node to terminal node.
  - *Measurement:* High-resolution timer (`time.perf_counter_ns()`) recorded in telemetry logs.
* **Metric D.4: Paired Baseline Comparison Ratio ($R_{\text{lat}}$)**
  - *Definition:* Ratio of protocol-mediated workflow latency to paired in-process baseline latency:
    $$R_{\text{lat}} = \frac{\text{Mean } T_{\text{wf}}(\text{MCP})}{\text{Mean } T_{\text{wf}}(\text{Baseline})}$$
  - *Methodological Rule:* The persistent MCP configuration amortizes repeated process initialization costs; measured latency includes session management and implementation runtime costs and should not be interpreted as isolated MCP protocol overhead.

---

## Group E: Reliability and Fault Handling

Measures the system's ability to detect faults, contain failure blast radius, protect downstream services, and release operating system resources.

* **Metric E.1: Failure Detection Rate ($R_{\text{det}}$)**
  - *Definition:* Percentage of injected service faults (tool exceptions, invalid schemas, process crashes) successfully caught and categorized by the orchestrator.
  - *Measurement:* Automated verification against injected error classifications.
* **Metric E.2: Downstream Execution Protection Rate ($R_{\text{prot}}$)**
  - *Definition:* Percentage of runs where an upstream failure strictly prevents downstream services from executing on invalid data:
    $$R_{\text{prot}} = \frac{\text{Runs where downstream was aborted}}{\text{Total upstream failure runs}} \times 100\%$$
* **Metric E.3: Partial Result Preservation Rate ($R_{\text{pres}}$)**
  - *Definition:* Percentage of runs where valid outputs generated by stages prior to the failure are safely preserved in the workflow state.
* **Metric E.4: Subprocess Cleanup Rate ($R_{\text{clean}}$)**
  - *Definition:* Verification that child processes are completely terminated upon workflow completion, error, or unhandled crash, preventing zombie processes.
  - *Measurement:* OS-level process table query via `psutil` verifying 0 orphan processes.

---

## Group F: AI Model and Decision Quality

Maintains strict separation between orchestration architecture metrics and individual AI algorithm accuracy.

* **Metric F.1: Demand Forecasting Accuracy**
  - *Metrics:* Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), Mean Absolute Percentage Error (MAPE).
  - *Evaluation Scope:* Evaluated against ground-truth historical sales data; kept independent from whether forecasting is invoked in-process or via MCP.
* **Metric F.2: Retail Operational KPIs**
  - *Metrics:* Stockout frequency, inventory holding cost, safety stock coverage ratio, gross margin.
  - *Evaluation Scope:* Operational business metrics evaluated in simulated market environments or partner deployments.
