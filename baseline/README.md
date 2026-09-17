# Tightly Coupled Baseline Architecture

## Purpose
This baseline implementation provides an experimental reference point to evaluate the architectural characteristics of the Model Context Protocol (MCP) in RetailOps. Specifically, it enables comparing:
1. **Service modularity & boundaries**: Direct in-process Python function calls vs. standard MCP stdio protocol interfaces.
2. **Execution overhead & latency**: In-process direct execution vs. inter-process communication (IPC) and separate process initialization.
3. **Extensibility & service replacement effort**: Modifying internal class bindings vs. swapping out an independent MCP server tool endpoint.

## Shared Logic vs. Architectural Differences

| Dimension | MCP Architecture (`client/orchestrator.py`) | Tightly Coupled Baseline (`baseline/tightly_coupled.py`) |
| :--- | :--- | :--- |
| **Workflow Stages** | 1. Catalog Enricher → 2. Forecasting → 3. Replenishment → 4. Pricing | 1. Catalog Enricher → 2. Forecasting → 3. Replenishment → 4. Pricing |
| **Domain Logic & Datasets** | Reads `sales_history.csv`, `events.json`, `competitor_prices.json`, etc. | Reuses identical datasets and calculations |
| **Communication Mechanism** | Stdio MCP protocol via `fastmcp` / `ClientSession` JSON-RPC | Direct Python synchronous in-process method invocation |
| **Process Model** | Subprocess per invocation / node execution (`python server.py`) | Single persistent Python interpreter memory space |
| **State Propagation** | LangGraph compiled graph passing `RetailOpsState` TypedDict | Sequential method execution passing structured dictionaries |
| **Telemetry System** | Common `TelemetryLogger` recording `architecture="mcp"` | Common `TelemetryLogger` recording `architecture="tightly_coupled"` |

## Latency Measurement Considerations
* **End-to-End Latency**: Total wall-clock time from workflow entry to result generation.
* **Architecture Overhead**: In the MCP architecture, each stage launches a separate Python interpreter over stdio, introducing process spawn latency, FastMCP server bootstrap, and JSON serialization. The tightly coupled baseline eliminates IPC and process spawning entirely.
* **External LLM Latency**: External API calls (such as OpenRouter) may exhibit high variance. For pure architectural comparisons, mock or deterministically controlled LLM conditions should be used.

## Baseline Scope Notice
This baseline is a minimal conventional in-process Python reference for academic evaluation of the MCP orchestration protocol overhead within the RetailOps repository; it is not a reproduction of Flowr or any other third-party system.
