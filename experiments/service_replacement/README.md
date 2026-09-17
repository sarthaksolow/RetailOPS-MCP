# Service Replacement Experiment: Forecasting Service

## 1. Research Question
Does replacing an enterprise retail AI service require fewer orchestration changes, fewer modified files, and fewer affected components in the Model Context Protocol (MCP) architecture compared with a conventional tightly coupled baseline?

## 2. Hypothesis
Because the MCP architecture decouples services behind a standardized protocol (stdio JSON-RPC tool contracts) and isolates them in separate processes, replacing a service implementation can be achieved with minimal or zero modification to downstream components, and primarily involves configuration changes (such as pointing to an alternative server binary/script). In contrast, in a tightly coupled baseline, service substitution requires direct in-process interface management, dependency passing, and internal method redirection or class refactoring.

*Note*: We make no assumption that MCP is inherently superior; rather, we empirically quantify the exact engineering footprint (files, components, schemas, lines, downstream impact) required to execute the same replacement across both paradigms.

## 3. Original Service Interface
The original Forecasting service (`servers/forecasting/server.py` and `direct_get_forecast` in `baseline/tightly_coupled.py`) defines:

- **Invocation Endpoint**:
  - MCP Tool: `getForecast(category: str, days_ahead: int = 30) -> dict`
  - Baseline Method: `direct_get_forecast(category: str, days_ahead: int = 30) -> Dict[str, Any]`
- **Input Parameters**:
  - `category` (string): Product category (e.g. `"tv"`, `"laptop"`, `"electronics"`).
  - `days_ahead` (integer, default 30): Forecasting horizon in days.
- **Output Schema (JSON / Dictionary)**:
  ```json
  {
    "category": "string",
    "base_forecast": 115.0,
    "seasonal_multiplier": 1.45,
    "historical_surge_factor": 1.8,
    "final_forecast": 300.15,
    "event": "Diwali",
    "narrative": "string"
  }
  ```
- **Domain Algorithm**:
  - 30-day simple moving average over `sales_history.csv`.
  - Seasonal multiplier lookup from `events.json` (within 180 days).
  - Event surge factor lookup from `surge_profile.json`.
  - Final forecast: `base_forecast * seasonal_multiplier * historical_surge_factor`.
  - Natural language narrative generation (OpenRouter LLM in MCP, template narrative in baseline).

## 4. Replacement Service Interface
The experimental replacement forecasting service (`servers/forecasting-replacement/server.py` and `baseline/replacement/forecasting_replacement.py`) defines:

- **Invocation Endpoint**:
  - MCP Tool: `getForecast(category: str, days_ahead: int = 30) -> dict`
  - Baseline Function: `replacement_direct_get_forecast(category: str, days_ahead: int = 30, sales_df=..., events=..., surge_profiles=..., moving_average_window: int = 60) -> Dict[str, Any]`
- **Algorithm Difference**:
  - Computes a deterministic 60-day moving average window (instead of 30 days).
  - Produces a deterministic template narrative without invoking remote LLM APIs, removing external network latency variance.
- **Schema Parity**:
  - 100% field parity (`category`, `base_forecast`, `seasonal_multiplier`, `historical_surge_factor`, `final_forecast`, `event`, `narrative`).
  - Strict preservation of types and semantics consumed by downstream Replenishment (`final_forecast`, `event`, `category`) and Pricing Strategy (`final_forecast`, `category`).

## 5. Shared Logic and Data
Both architectures and both service versions operate on identical underlying retail data files:
1. `servers/forecasting/data/sales_history.csv`
2. `servers/forecasting/data/events.json`
3. `servers/forecasting/data/surge_profile.json`

## 6. Architectural Differences

| Dimension | MCP Architecture | Tightly Coupled Baseline |
| :--- | :--- | :--- |
| **Service Boundary** | Separate process communicating over stdio JSON-RPC | In-process module / function call sharing interpreter memory |
| **Coupling Mechanism** | Protocol-level contract (`FastMCP` tool definition) | Language-level Python function signature and object state |
| **Activation Method** | Configuration / Environment Variable (`RETAILOPS_FORECASTING_SERVER_PATH`) | Constructor dependency injection / function pointer passing |
| **Failure Isolation** | Process crash in forecasting server is trapped as IPC error; does not corrupt orchestrator heap | Unhandled exception in forecasting function bubbles up orchestrator call stack directly |
| **Data Access** | Subprocess loads and parses data files independently | Shared in-memory `DataFrame` and dictionary references |

## 7. Measurement Definitions
1. **Orchestration files modified**: Count of files in the orchestration layer (`client/` or `baseline/`) that required code modifications to allow swapping the service.
2. **Service implementation files modified**: Count of existing service implementation files modified. (Must be 0 to preserve existing implementations).
3. **Affected components**: Count of distinct architectural components or nodes impacted by the replacement.
4. **Interface or schema changes**: Count of field additions, removals, or type modifications across the service boundary.
5. **Downstream modifications**: Whether Replenishment, Pricing Strategy, or state aggregation required any changes.
6. **Changed functions**: Count of existing functions modified in the repository to support replacement.
7. **Integration time**: Measured time to execute swap under test conditions, or noted as "Not measured" if human developer effort.
8. **Restorability of original service**: Whether reverting to the original service requires code edits or simple configuration toggle.
9. **Existing tests passing**: Pass/fail verification of the existing test suite (`test_integration.py`, `test_instrumentation.py`, `test_baseline_comparison.py`, `client/test_client.py`).

## 8. Exact Commands Used
```powershell
$env:PYTHONIOENCODING='utf-8'; python test_instrumentation.py
$env:PYTHONIOENCODING='utf-8'; python test_baseline_comparison.py
$env:PYTHONIOENCODING='utf-8'; python test_service_replacement.py
$env:PYTHONIOENCODING='utf-8'; python test_integration.py
$env:PYTHONIOENCODING='utf-8'; python client/test_client.py
```

## 9. Experimental Limitations
- **Synthetic Single-Node Deployment**: Both MCP servers run locally on Windows as child processes via stdio rather than over a network (SSE / HTTP).
- **Process Spawn Overhead**: FastMCP process initialization adds ~1-2s per stage in Python, which is an artifact of spawning child interpreters per step rather than maintaining persistent daemons.
- **Dataset Uniformity**: The synthetic sales dataset contains cyclical seasonal patterns where 30-day and 60-day moving averages yield close base estimates for specific categories.
- **Human Authoring Time**: We do not measure cognitive developer time or subjective ergonomics, focusing strictly on objective structural metrics (files, functions, interfaces, tests).

## 10. Scope and Non-Reproduction Notice
This experiment is designed specifically to test the modularity and replacement effort of enterprise retail services within the RetailOps codebase. It is not a reproduction or evaluation of Flowr or any other external orchestration framework.
