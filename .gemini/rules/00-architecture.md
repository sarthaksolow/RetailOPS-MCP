---
globs:
  - "**/*.py"
---
# 🏗️ System Architecture Conventions

## Integration Workflow
- Any end-to-end features must go through the Catalog Enricher, Forecasting, Replenishment, and Pricing servers in a structured graph pattern.
- Graph State must be maintained using `RetailOpsState` defined in [orchestrator.py](file:///E:/Repositories/RetailOPS-MCP/client/orchestrator.py).

## Error Propagation
- Each workflow step must capture exceptions and append them to `state["errors"]` instead of crashing the entire graph, unless it is a fatal initialization error.
- Partial outputs must be returned even in case of non-fatal downstream failures.
