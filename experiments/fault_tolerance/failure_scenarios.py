"""
Fault Injection and Failure Scenarios Definition for RetailOps (Task 07).
Provides controlled, deterministic failure injection mechanisms for:
- Scenario A: Catalog Enricher Failure
- Scenario B: Forecasting Failure
- Scenario C: Replenishment Failure
- Scenario D: Pricing Strategy Failure
- Scenario E: Persistent MCP Tool Failure
- Scenario F: MCP Process Termination / Crash

All failures are injected deterministically via test-only environment variables
or dedicated fault configurations without altering production business logic.
"""
import os
import sys
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

# Ensure root dir in path
from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Standard fault injection environment variable names
ENV_FAILURE_SERVICE = "RETAILOPS_FAILURE_SERVICE"      # "enricher" | "forecasting" | "replenishment" | "pricing" | "all" | "none"
ENV_FAILURE_MODE = "RETAILOPS_FAILURE_MODE"            # "tool_error" | "crash_exit" | "invalid_response" | "timeout"
ENV_FAILURE_MESSAGE = "RETAILOPS_FAILURE_MESSAGE"      # Custom error message string


@dataclass
class FailureScenarioMetadata:
    """Metadata and formal expectations for a failure scenario."""
    scenario_id: str
    target_service: str
    failure_mode: str
    description: str
    expected_workflow_status: str
    expected_failed_steps: list
    expected_completed_steps: list
    partial_results_expected: bool
    downstream_protection_expected: bool
    expected_error_substring: str


# Catalog of defined failure scenarios
SCENARIOS: Dict[str, FailureScenarioMetadata] = {
    "scenario_a_enricher_failure": FailureScenarioMetadata(
        scenario_id="scenario_a_enricher_failure",
        target_service="enricher",
        failure_mode="tool_error",
        description="Catalog Enricher fails during tool execution; workflow records error, assigns fallback category, and continues or stops safely.",
        expected_workflow_status="failed_forecast", # Since enrichment error sets category to general, forecasting fails because general has no forecast data in deterministic tables
        expected_failed_steps=["enrich", "forecast"],
        expected_completed_steps=[],
        partial_results_expected=False,
        downstream_protection_expected=True,
        expected_error_substring="Enrichment"
    ),
    "scenario_b_forecasting_failure": FailureScenarioMetadata(
        scenario_id="scenario_b_forecasting_failure",
        target_service="forecasting",
        failure_mode="tool_error",
        description="Forecasting service fails; Catalog enrichment result is preserved; Replenishment and Pricing are prevented from using invalid forecast.",
        expected_workflow_status="failed_forecast",
        expected_failed_steps=["forecast"],
        expected_completed_steps=["enrich"],
        partial_results_expected=True,
        downstream_protection_expected=True,
        expected_error_substring="Forecasting"
    ),
    "scenario_c_replenishment_failure": FailureScenarioMetadata(
        scenario_id="scenario_c_replenishment_failure",
        target_service="replenishment",
        failure_mode="tool_error",
        description="Replenishment service fails; Catalog and Forecast results are preserved; Pricing is prevented from executing on incomplete replenishment.",
        expected_workflow_status="failed_replenishment",
        expected_failed_steps=["replenish"],
        expected_completed_steps=["enrich", "forecast"],
        partial_results_expected=True,
        downstream_protection_expected=True,
        expected_error_substring="Replenishment"
    ),
    "scenario_d_pricing_failure": FailureScenarioMetadata(
        scenario_id="scenario_d_pricing_failure",
        target_service="pricing",
        failure_mode="tool_error",
        description="Pricing Strategy fails; Enricher, Forecast, and Replenishment results are all preserved in partial results.",
        expected_workflow_status="failed_pricing",
        expected_failed_steps=["price"],
        expected_completed_steps=["enrich", "forecast", "replenish"],
        partial_results_expected=True,
        downstream_protection_expected=True, # Pricing is the terminal step
        expected_error_substring="Pricing"
    ),
    "scenario_e_persistent_tool_failure": FailureScenarioMetadata(
        scenario_id="scenario_e_persistent_tool_failure",
        target_service="replenishment",
        failure_mode="tool_error",
        description="Replenishment fails over persistent MCP session pool; Session remains open and cleans up without leaking state to subsequent calls.",
        expected_workflow_status="failed_replenishment",
        expected_failed_steps=["replenish"],
        expected_completed_steps=["enrich", "forecast"],
        partial_results_expected=True,
        downstream_protection_expected=True,
        expected_error_substring="Replenishment"
    ),
    "scenario_f_process_termination": FailureScenarioMetadata(
        scenario_id="scenario_f_process_termination",
        target_service="forecasting",
        failure_mode="crash_exit",
        description="Forecasting server process terminates abruptly (exit code 1); Client catches process exit, avoids hanging, and records failure safely.",
        expected_workflow_status="failed_forecast",
        expected_failed_steps=["forecast"],
        expected_completed_steps=["enrich"],
        partial_results_expected=True,
        downstream_protection_expected=True,
        expected_error_substring="Forecasting"
    )
}


import tempfile

FAULT_SIGNAL_FILE = Path(tempfile.gettempdir()) / "retailops_fault_signal.json"

class FaultInjectionContext:
    """
    Context manager to inject deterministic faults during test execution
    and restore the previous environment afterwards.
    Supports both environment variables (for fresh subprocesses) and
    a temporary signal file (for already-running persistent subprocesses).
    """

    def __init__(
        self,
        service: str,
        mode: str = "tool_error",
        message: Optional[str] = None
    ):
        self.service = service
        self.mode = mode
        self.message = message or f"Deterministic fault injected in {service} ({mode})"
        self.previous_env = {}

    def __enter__(self):
        env_vars = {
            ENV_FAILURE_SERVICE: self.service,
            ENV_FAILURE_MODE: self.mode,
            ENV_FAILURE_MESSAGE: self.message
        }
        for k, v in env_vars.items():
            self.previous_env[k] = os.environ.get(k)
            os.environ[k] = v

        signal_data = {
            "service": self.service,
            "mode": self.mode,
            "message": self.message
        }
        content = json.dumps(signal_data)
        with open(FAULT_SIGNAL_FILE, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for k, prev_v in self.previous_env.items():
            if prev_v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prev_v

        try:
            if FAULT_SIGNAL_FILE.exists():
                FAULT_SIGNAL_FILE.unlink()
        except Exception:
            pass


def classify_error(error_str: str) -> str:
    """
    Categorize failure message into standardized taxonomy:
    - tool_level_exception
    - mcp_communication_failure
    - server_initialization_failure
    - subprocess_termination
    - timeout
    - invalid_response
    - unknown_error
    """
    if not error_str:
        return "none"
    err_low = error_str.lower()
    if "timeout" in err_low or "timed out" in err_low:
        return "timeout"
    if "crash" in err_low or "exit" in err_low or "taskgroup" in err_low or "broken pipe" in err_low or "connection closed" in err_low:
        return "subprocess_termination"
    if "initialize" in err_low or "handshake" in err_low:
        return "server_initialization_failure"
    if "corrupt" in err_low or "no valid text content" in err_low or "parse" in err_low:
        return "invalid_response"
    if "stdio" in err_low or "pipe" in err_low or "communication" in err_low:
        return "mcp_communication_failure"
    if "error" in err_low or "exception" in err_low or "injected" in err_low or "fail" in err_low:
        return "tool_level_exception"
    return "unknown_error"


def should_inject_fault(service_name: str) -> Optional[Dict[str, str]]:
    """
    Utility called inside mock servers to inspect if a fault should be triggered.
    Checks signal file first (for persistent servers), then environment variables.
    """
    try:
        if FAULT_SIGNAL_FILE.exists():
            with open(FAULT_SIGNAL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                sig_target = data.get("service", "").lower()
                if sig_target in [service_name.lower(), "all"]:
                    return {
                        "mode": data.get("mode", "tool_error"),
                        "message": data.get("message", f"Injected fault in {service_name}")
                    }
    except Exception:
        pass

    target = os.getenv(ENV_FAILURE_SERVICE, "").lower()
    if target in [service_name.lower(), "all"]:
        return {
            "mode": os.getenv(ENV_FAILURE_MODE, "tool_error"),
            "message": os.getenv(ENV_FAILURE_MESSAGE, f"Injected fault in {service_name}")
        }
    return None

