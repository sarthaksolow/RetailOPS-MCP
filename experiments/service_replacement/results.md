# Service Replacement Experiment: Results

This document presents empirical measurements comparing the service replacement effort between the Model Context Protocol (MCP) architecture and the conventional tightly coupled baseline in RetailOps.

## Comparative Measurement Table

| Metric | MCP Architecture | Tightly Coupled Baseline | Measurement Method |
|---|---:|---:|---|
| **Orchestration files modified** | 1 (`client/orchestrator.py`) | 2 (`baseline/tightly_coupled.py`, `baseline/__init__.py`) | Git diff / file modification count |
| **Service files modified** | 0 (`servers/forecasting/server.py` unchanged) | 0 (original baseline methods unchanged) | File hash / git diff verification |
| **Affected components** | 1 (`forecasting` node connector) | 2 (`TightlyCoupledRetailOps` class, workflow coordinator) | Dependency graph inspection |
| **Downstream modifications** | 0 (No changes to replenish or price) | 0 (No changes to replenish or price) | Code inspection of downstream stages |
| **Interface changes** | 0 (100% schema parity on `getForecast`) | 0 (100% dictionary field contract parity) | Schema and key comparison |
| **Changed functions** | 1 (`MCPServerManager.__init__`) | 2 (`TightlyCoupledRetailOps.__init__`, `run_full_workflow`) | AST / Git hunk inspection |
| **Integration time** | Not measured | Not measured | Developer implementation time not timed |
| **Original service restorability** | Full (unset env var or set to default path) | Full (instantiate default without parameter) | Functional testing of fallback |
| **Existing tests passing** | 100% (All existing suites pass) | 100% (All existing suites pass) | Automated test suite execution |

## Key Observations

1. **Service Decoupling**:
   - In the **MCP Architecture**, service replacement was achieved by creating an independent server (`servers/forecasting-replacement/server.py`) and pointing `RETAILOPS_FORECASTING_SERVER_PATH` to it. Neither the LangGraph graph structure, nor the prompt logic, nor downstream node functions required any modification.
   - In the **Tightly Coupled Baseline**, service replacement required supporting dependency injection in the class constructor and adapting the internal call dispatch inside `run_full_workflow`, because in-process function invocation binds tightly to caller parameter signatures.

2. **Downstream Invariance**:
   - Both architectures demonstrated 0 downstream modifications: because both replacement services preserved the exact output dictionary contract (`category`, `base_forecast`, `seasonal_multiplier`, `historical_surge_factor`, `final_forecast`, `event`, `narrative`), the Replenishment and Pricing Strategy stages executed seamlessly without errors.

3. **Protocol vs. In-Process Boundary**:
   - MCP enforces a process and protocol boundary. The replacement service could theoretically be written in a different programming language (e.g., TypeScript or Go) as long as it speaks the MCP stdio protocol.
   - The tightly coupled baseline requires identical runtime language execution (Python 3.12) and object compatibility.
