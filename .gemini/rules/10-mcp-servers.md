---
globs:
  - "servers/**/*.py"
---
# 🔌 MCP Server Development Conventions

## STDIO Safety (Critical)
- **Rule**: Never use `print()` or output to `stdout` inside server code. Any log messages, debug prints, or tracebacks must be output to `sys.stderr` via `sys.stderr.write()` or standard python logging configured to write to stderr.
- **Reason**: Standard output (`stdout`) is reserved for MCP JSON-RPC protocol messages. Writing plain text to stdout corrupts the protocol stream and crashes client connections.

## Tool Definitions
- Use `@app.tool()` decorators from `FastMCP`.
- Ensure all arguments have type hints and explicit descriptions in docstrings.
- Return structured data (dict) whenever possible to facilitate JSON parsing by the client.

## OpenRouter/LLM Fallbacks
- Wrap all OpenRouter API calls in robust `try-except` blocks.
- If the API key is missing or the external API call fails, the tool must gracefully fall back to local rule-based narratives or pre-defined templates rather than failing the execution.
