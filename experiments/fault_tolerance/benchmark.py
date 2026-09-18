"""
Fault Tolerance and Failure-Recovery Benchmark for RetailOps (Task 07).

Executes controlled, reproducible failure-injection benchmarks across 6 failure scenarios:
- Scenario A: Catalog Enricher Failure
- Scenario B: Forecasting Failure
- Scenario C: Replenishment Failure
- Scenario D: Pricing Strategy Failure
- Scenario E: Persistent MCP Tool Failure
- Scenario F: Process Termination / Crash Exit

Evaluates 5 quantitative recovery metrics:
1. Failure Detection Rate (%)
2. Expected Behavior Rate (%)
3. Partial-Result Preservation Rate (%)
4. Downstream Protection Rate (%)
5. Cleanup Success Rate (%)

Outputs:
- raw_results.jsonl
- summary.json
"""
import os
import sys
import json
import time
import uuid
import asyncio
import argparse
import psutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "client"))

from experiments.fault_tolerance.failure_scenarios import (
    SCENARIOS,
    FailureScenarioMetadata,
    FaultInjectionContext,
    classify_error
)
from client.telemetry import now_iso
from experiments.performance_benchmark.benchmark import run_deterministic_mcp
from client.persistent_client import PersistentMCPSessionPool, PersistentRetailOpsClient


MOCK_SERVER_PATHS = {
    "enricher": ROOT_DIR / "servers" / "mock-deterministic" / "enricher_server.py",
    "forecasting": ROOT_DIR / "servers" / "forecasting-replacement" / "server.py",
    "replenishment": ROOT_DIR / "servers" / "mock-deterministic" / "replenishment_server.py",
    "pricing": ROOT_DIR / "servers" / "mock-deterministic" / "pricing_server.py"
}


def evaluate_run(
    scenario_meta: FailureScenarioMetadata,
    workflow_result: Dict[str, Any],
    cleanup_successful: bool,
    os_process_cleanup_verified: bool,
    latency_ms: float
) -> Dict[str, Any]:
    """
    Evaluate an individual execution against scenario specifications.
    """
    status = workflow_result.get("status", "unknown")
    failed_steps = workflow_result.get("failed_steps", [])
    completed_steps = workflow_result.get("completed_steps", [])
    errors = workflow_result.get("errors", [])
    partial_result = workflow_result.get("partial_result", {})

    # 1. Failure Detection: was the failure detected in errors or status?
    has_errors = len(errors) > 0
    status_indicates_failure = "failed" in status or status != "completed"
    failure_detected = has_errors or status_indicates_failure

    # 2. Expected Behavior: status and failed steps match metadata expectation
    status_matches = (status == scenario_meta.expected_workflow_status)
    # Check that expected failed step is in failed_steps
    failed_steps_match = all(step in failed_steps for step in scenario_meta.expected_failed_steps)
    expected_behavior = status_matches and failed_steps_match and failure_detected

    # 3. Partial Results Preservation: are outputs of completed steps preserved?
    partial_preserved = True
    if scenario_meta.partial_results_expected:
        for step in scenario_meta.expected_completed_steps:
            if step == "enrich":
                p_cat = partial_result.get("category") or partial_result.get("enrichment", {}).get("category")
                if not p_cat or p_cat == "general":
                    # For scenario B, TV maps to electronics
                    if workflow_result.get("product_name") == "Samsung TV" and p_cat != "electronics":
                        partial_preserved = False
            elif step == "forecast":
                p_fc = partial_result.get("forecast", {}).get("final")
                if p_fc is None or p_fc <= 0:
                    partial_preserved = False
            elif step == "replenish":
                p_rep = partial_result.get("replenishment", {}).get("reorder_qty")
                if p_rep is None:
                    partial_preserved = False
    else:
        partial_preserved = True  # Not required or expected empty

    # 4. Downstream Protection: were downstream steps protected from bad/missing data?
    # Downstream steps should NOT be in completed_steps
    downstream_protected = True
    if scenario_meta.target_service == "enricher":
        # replenishment and pricing should not run/succeed
        downstream_protected = "replenish" not in completed_steps and "price" not in completed_steps
    elif scenario_meta.target_service == "forecasting":
        downstream_protected = "replenish" not in completed_steps and "price" not in completed_steps
    elif scenario_meta.target_service == "replenishment":
        downstream_protected = "price" not in completed_steps
    elif scenario_meta.target_service == "pricing":
        downstream_protected = True  # pricing is terminal

    # 5. Error Classification
    primary_error_msg = errors[0] if errors else ""
    error_class = classify_error(primary_error_msg)

    return {
        "failure_detected": failure_detected,
        "expected_behavior": expected_behavior,
        "partial_results_preserved": partial_preserved,
        "downstream_protected": downstream_protected,
        "cleanup_successful": cleanup_successful,
        "os_process_cleanup_verified": os_process_cleanup_verified,
        "error_classification": error_class,
        "primary_error": primary_error_msg,
        "workflow_status": status,
        "completed_steps": completed_steps,
        "failed_steps": failed_steps,
        "latency_ms": latency_ms
    }


async def run_scenario_iteration(scenario_id: str, repetition: int) -> Dict[str, Any]:
    """Execute a single repetition of a given scenario."""
    meta = SCENARIOS[scenario_id]
    product = "Samsung TV"
    run_id = f"ft-{scenario_id[:10]}-rep{repetition}-{uuid.uuid4().hex[:6]}"
    start_iso = now_iso()
    t_start = time.perf_counter()

    cleanup_ok = True
    os_process_cleanup_verified = True
    workflow_result = {}

    current_proc = psutil.Process(os.getpid())
    before_pids = {c.pid for c in current_proc.children(recursive=True)}

    if scenario_id == "scenario_e_persistent_tool_failure":
        # Use PersistentMCPSessionPool
        try:
            async with PersistentMCPSessionPool(server_paths=MOCK_SERVER_PATHS) as pool:
                client = PersistentRetailOpsClient(pool)
                with FaultInjectionContext(
                    service=meta.target_service,
                    mode=meta.failure_mode,
                    message=f"Injected persistent failure in {meta.target_service}"
                ):
                    workflow_result = await client.run_full_workflow(product)
            cleanup_ok = True
        except Exception as e:
            cleanup_ok = False
            workflow_result = {
                "status": "exception",
                "errors": [str(e)],
                "failed_steps": ["pool_execution"],
                "completed_steps": []
            }
    else:
        # Standard MCP Process-per-Call execution
        try:
            with FaultInjectionContext(
                service=meta.target_service,
                mode=meta.failure_mode,
                message=f"Deterministic failure injected in {meta.target_service} ({meta.failure_mode})"
            ):
                workflow_result = await run_deterministic_mcp(product, days_ahead=30)
            cleanup_ok = True
        except Exception as e:
            cleanup_ok = False
            workflow_result = {
                "status": "exception",
                "errors": [str(e)],
                "failed_steps": [meta.target_service],
                "completed_steps": []
            }

    # OS-level process cleanup check with timeout
    t_check_start = time.perf_counter()
    while time.perf_counter() - t_check_start < 2.0:
        active_children = [
            c for c in current_proc.children(recursive=True)
            if c.is_running() and c.status() != psutil.STATUS_ZOMBIE and c.pid not in before_pids
        ]
        if not active_children:
            break
        time.sleep(0.1)

    final_active_children = [
        c for c in current_proc.children(recursive=True)
        if c.is_running() and c.status() != psutil.STATUS_ZOMBIE and c.pid not in before_pids
    ]
    os_process_cleanup_verified = (len(final_active_children) == 0)

    t_end = time.perf_counter()
    duration_ms = round((t_end - t_start) * 1000, 2)
    end_iso = now_iso()

    eval_metrics = evaluate_run(meta, workflow_result, cleanup_ok, os_process_cleanup_verified, duration_ms)

    record = {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "target_service": meta.target_service,
        "failure_mode": meta.failure_mode,
        "repetition": repetition,
        "start_time": start_iso,
        "end_time": end_iso,
        "duration_ms": duration_ms,
        "evaluation": eval_metrics,
        "workflow_status": eval_metrics["workflow_status"],
        "completed_steps": eval_metrics["completed_steps"],
        "failed_steps": eval_metrics["failed_steps"],
        "errors": workflow_result.get("errors", []),
        "error_classification": eval_metrics["error_classification"]
    }
    return record


def execute_fault_tolerance_benchmark(
    repetitions: int = 10,
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Execute all failure scenarios for specified repetitions and output summary."""
    out_path = output_dir or (ROOT_DIR / "experiments" / "fault_tolerance")
    out_path.mkdir(parents=True, exist_ok=True)
    raw_file = out_path / "raw_results.jsonl"
    summary_file = out_path / "summary.json"

    print(f"\n{'='*70}\n[TASK 07] STARTING FAULT TOLERANCE & RECOVERY BENCHMARK\n{'='*70}")
    print(f"Scenarios: {len(SCENARIOS)}")
    print(f"Repetitions per scenario: {repetitions}")
    print(f"Target file: {raw_file}\n")

    all_records = []

    for scen_id, meta in SCENARIOS.items():
        print(f"--- Running {scen_id} ({meta.target_service} / {meta.failure_mode}) ---")
        for rep in range(1, repetitions + 1):
            rec = asyncio.run(run_scenario_iteration(scen_id, rep))
            all_records.append(rec)
            ev = rec["evaluation"]
            print(
                f"  [{rep}/{repetitions}] {rec['scenario_id']}: status={rec['workflow_status']} | "
                f"detected={ev['failure_detected']} | expected_behavior={ev['expected_behavior']} | "
                f"downstream_protected={ev['downstream_protected']} | cleanup={ev['cleanup_successful']} | "
                f"latency={rec['duration_ms']:.2f} ms"
            )

    # Write raw_results.jsonl
    with open(raw_file, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r) + "\n")

    # Aggregate summary metrics
    summary = compute_fault_tolerance_summary(all_records)

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[SUCCESS] Benchmark completed. Results saved to:\n- {raw_file}\n- {summary_file}")
    return summary


def compute_fault_tolerance_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate per-scenario metrics into structured summary report."""
    summary: Dict[str, Any] = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_runs": len(records),
            "environment": {
                "os": os.name,
                "platform": sys.platform,
                "python_version": sys.version.split()[0]
            }
        },
        "scenarios": {},
        "overall": {}
    }

    # Group by scenario
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        scen = r["scenario_id"]
        grouped.setdefault(scen, []).append(r)

    total_runs_all = len(records)
    total_detected = 0
    total_expected = 0
    total_partial_preserved = 0
    total_downstream_protected = 0
    total_cleanup_ok = 0
    total_os_proc_cleaned = 0
    all_latencies = []

    for scen, recs in grouped.items():
        n = len(recs)
        det_cnt = sum(1 for r in recs if r["evaluation"]["failure_detected"])
        exp_cnt = sum(1 for r in recs if r["evaluation"]["expected_behavior"])
        part_cnt = sum(1 for r in recs if r["evaluation"]["partial_results_preserved"])
        down_cnt = sum(1 for r in recs if r["evaluation"]["downstream_protected"])
        clean_cnt = sum(1 for r in recs if r["evaluation"]["cleanup_successful"])
        os_proc_cnt = sum(1 for r in recs if r["evaluation"].get("os_process_cleanup_verified", False))
        latencies = [r["duration_ms"] for r in recs]
        err_classes = [r["error_classification"] for r in recs]

        total_detected += det_cnt
        total_expected += exp_cnt
        total_partial_preserved += part_cnt
        total_downstream_protected += down_cnt
        total_cleanup_ok += clean_cnt
        total_os_proc_cleaned += os_proc_cnt
        all_latencies.extend(latencies)

        summary["scenarios"][scen] = {
            "repetitions": n,
            "target_service": recs[0]["target_service"],
            "failure_mode": recs[0]["failure_mode"],
            "metrics": {
                "failure_detection_rate_pct": round((det_cnt / n) * 100, 2),
                "expected_behavior_rate_pct": round((exp_cnt / n) * 100, 2),
                "partial_result_preservation_rate_pct": round((part_cnt / n) * 100, 2),
                "downstream_protection_rate_pct": round((down_cnt / n) * 100, 2),
                "cleanup_success_rate_pct": round((clean_cnt / n) * 100, 2),
                "os_process_cleanup_rate_pct": round((os_proc_cnt / n) * 100, 2)
            },
            "latency_ms": {
                "mean": round(sum(latencies) / n, 2),
                "min": round(min(latencies), 2),
                "max": round(max(latencies), 2)
            },
            "primary_error_classifications": list(set(err_classes))
        }

    summary["overall"] = {
        "total_executions": total_runs_all,
        "overall_failure_detection_rate_pct": round((total_detected / total_runs_all) * 100, 2) if total_runs_all else 0.0,
        "overall_expected_behavior_rate_pct": round((total_expected / total_runs_all) * 100, 2) if total_runs_all else 0.0,
        "overall_partial_result_preservation_rate_pct": round((total_partial_preserved / total_runs_all) * 100, 2) if total_runs_all else 0.0,
        "overall_downstream_protection_rate_pct": round((total_downstream_protected / total_runs_all) * 100, 2) if total_runs_all else 0.0,
        "overall_cleanup_success_rate_pct": round((total_cleanup_ok / total_runs_all) * 100, 2) if total_runs_all else 0.0,
        "overall_os_process_cleanup_rate_pct": round((total_os_proc_cleaned / total_runs_all) * 100, 2) if total_runs_all else 0.0,
        "mean_latency_ms": round(sum(all_latencies) / len(all_latencies), 2) if all_latencies else 0.0
    }

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Task 07 Fault Tolerance Benchmark")
    parser.add_argument("--repetitions", type=int, default=10, help="Measured repetitions per scenario (default: 10)")
    args = parser.parse_args()

    execute_fault_tolerance_benchmark(repetitions=args.repetitions)
