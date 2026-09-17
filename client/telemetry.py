"""
Execution telemetry models and structured logger for RetailOps.
Records execution-level and per-service telemetry for research evaluation.
"""
import os
import json
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

# Default log directory
DEFAULT_LOG_DIR = Path(__file__).parent.parent / "logs"


def get_telemetry_log_path() -> Path:
    """Resolve the path to the telemetry JSON lines log file."""
    custom_path = os.getenv("RETAILOPS_TELEMETRY_LOG")
    if custom_path:
        p = Path(custom_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_LOG_DIR / "telemetry.jsonl"


def now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ServiceCallTelemetry:
    """Telemetry data for a single MCP service/tool invocation."""
    service_name: str
    tool_name: str
    start_time: str
    end_time: str
    duration_ms: float
    status: str  # "success" | "failure"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionTelemetry:
    """Execution-level telemetry for a workflow run."""
    execution_id: str
    workflow_name: str
    product_name: str
    category: Optional[str]
    start_time: str
    end_time: str
    total_duration_ms: float
    workflow_status: str  # e.g. "completed", "failed_forecast", "error"
    completed_steps: List[str]
    failed_steps: List[str]
    service_calls: List[Dict[str, Any]]
    partial_result: Dict[str, Any]
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TelemetryLogger:
    """Structured telemetry logger writing machine-readable JSON lines."""

    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = Path(log_file) if log_file else get_telemetry_log_path()

    @staticmethod
    def sanitize(obj: Any) -> Any:
        """Recursively scrub sensitive keys (API keys, secrets, auth headers)."""
        sensitive_keywords = {"key", "token", "secret", "auth", "password", "credential"}
        if isinstance(obj, dict):
            clean_dict = {}
            for k, v in obj.items():
                if any(kw in str(k).lower() for kw in sensitive_keywords):
                    clean_dict[k] = "[REDACTED]"
                else:
                    clean_dict[k] = TelemetryLogger.sanitize(v)
            return clean_dict
        elif isinstance(obj, list):
            return [TelemetryLogger.sanitize(item) for item in obj]
        return obj

    def log_execution(self, telemetry: ExecutionTelemetry) -> None:
        """Write an execution telemetry record to the JSON lines file."""
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            record = self.sanitize(telemetry.to_dict())
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            # Fallback print to stderr to avoid breaking main workflow
            import sys
            print(f"[TELEMETRY ERROR] Failed to write telemetry: {e}", file=sys.stderr)
