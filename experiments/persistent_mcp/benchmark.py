"""
Controlled Performance Benchmark for Task 06:
Persistent MCP Server and Process-Lifecycle Overhead Analysis.

Compares three architectures under identical deterministic workloads:
1. Condition A: Tightly Coupled Baseline (direct Python in-process)
2. Condition B: MCP Process-per-Call (standard LangGraph orchestrator launching servers per node)
3. Condition C: Persistent MCP Process (long-lived MCP session pool reusing servers across calls)

Records fine-grained timing boundaries:
- Directly measured metrics: process spawn, session handshake, tool execution, shutdown, total workflow latency.
- Derived metrics: architectural differences, lifecycle overhead ratios.
"""
import os
import sys
import json
import time
import uuid
import asyncio
import argparse
import statistics
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "client"))

from client.orchestrator import RetailOpsClient
from client.persistent_client import PersistentMCPSessionPool, PersistentRetailOpsClient
from baseline.tightly_coupled import TightlyCoupledRetailOps
from baseline.replacement.forecasting_replacement import replacement_direct_get_forecast
from client.telemetry import now_iso


def run_deterministic_tightly_coupled(product: str, days_ahead: int = 30) -> Dict[str, Any]:
    """Condition A: In-process direct function execution."""
    tc = TightlyCoupledRetailOps(forecasting_service=replacement_direct_get_forecast)
    return tc.run_full_workflow(product, days_ahead=days_ahead)


async def run_deterministic_mcp_process_per_call(product: str, days_ahead: int = 30) -> Dict[str, Any]:
    """Condition B: MCP process-per-call (standard orchestrator)."""
    old_env = {}
    deterministic_env = {
        "RETAILOPS_ENRICHER_SERVER_PATH": str(ROOT_DIR / "servers" / "mock-deterministic" / "enricher_server.py"),
        "RETAILOPS_FORECASTING_SERVER_PATH": str(ROOT_DIR / "servers" / "forecasting-replacement" / "server.py"),
        "RETAILOPS_REPLENISHMENT_SERVER_PATH": str(ROOT_DIR / "servers" / "mock-deterministic" / "replenishment_server.py"),
        "RETAILOPS_PRICING_SERVER_PATH": str(ROOT_DIR / "servers" / "mock-deterministic" / "pricing_server.py")
    }
    for k, v in deterministic_env.items():
        old_env[k] = os.environ.get(k)
        os.environ[k] = v

    try:
        client = RetailOpsClient()
        return await client.run_full_workflow(product, days_ahead=days_ahead)
    finally:
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def calculate_metrics(durations: List[float]) -> Dict[str, Any]:
    """Calculate descriptive summary statistics."""
    if not durations:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
            "std_dev": None,
            "p95": None
        }
    sorted_durations = sorted(durations)
    n = len(sorted_durations)
    p95_idx = int(round(0.95 * (n - 1)))
    p95 = sorted_durations[p95_idx]

    return {
        "count": n,
        "mean": round(statistics.mean(durations), 2),
        "median": round(statistics.median(durations), 2),
        "min": round(min(durations), 2),
        "max": round(max(durations), 2),
        "std_dev": round(statistics.stdev(durations), 2) if n > 1 else 0.0,
        "p95": round(p95, 2)
    }


def compute_benchmark_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary statistics aggregated by architecture and condition."""
    measured_records = [r for r in records if not r.get("warmup", False)]

    summary = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "environment": {
                "os": os.name,
                "platform": sys.platform,
                "python_version": sys.version.split()[0]
            }
        }
    }

    arch_groups = {
        "tightly_coupled": [r for r in measured_records if r["architecture"] == "tightly_coupled"],
        "mcp_process_per_call": [r for r in measured_records if r["architecture"] == "mcp_process_per_call"],
        "persistent_mcp": [r for r in measured_records if r["architecture"] == "persistent_mcp"]
    }

    for arch_key, arch_recs in arch_groups.items():
        total = len(arch_recs)
        successful = sum(1 for r in arch_recs if r.get("workflow_status") == "completed")
        failed = total - successful
        completion_rate = round((successful / total) * 100, 2) if total > 0 else 0.0

        durations = [r["total_duration_ms"] for r in arch_recs if r.get("workflow_status") == "completed"]
        overall_stats = calculate_metrics(durations)

        # Per service stats
        services = ["Catalog Enricher", "Forecasting", "Replenishment", "Pricing Strategy"]
        per_service = {}
        for s in services:
            s_durations = [
                r["service_durations_ms"].get(s)
                for r in arch_recs
                if r.get("workflow_status") == "completed" and s in r.get("service_durations_ms", {})
            ]
            per_service[s] = calculate_metrics([d for d in s_durations if d is not None])

        summary[arch_key] = {
            "total_runs": total,
            "successful_runs": successful,
            "failed_runs": failed,
            "completion_rate": completion_rate,
            "overall_runtime_ms": overall_stats,
            "per_service_ms": per_service
        }

    # Derived comparisons
    tc_mean = summary["tightly_coupled"]["overall_runtime_ms"]["mean"]
    mcp_ppc_mean = summary["mcp_process_per_call"]["overall_runtime_ms"]["mean"]
    pers_mean = summary["persistent_mcp"]["overall_runtime_ms"]["mean"]

    summary["derived_comparisons"] = {
        "tc_mean_ms": tc_mean,
        "mcp_process_per_call_mean_ms": mcp_ppc_mean,
        "persistent_mcp_mean_ms": pers_mean,
        "process_per_call_vs_persistent_diff_ms": round(mcp_ppc_mean - pers_mean, 2) if (mcp_ppc_mean and pers_mean) else None,
        "persistent_speedup_factor_vs_process_per_call": round(mcp_ppc_mean / pers_mean, 2) if (mcp_ppc_mean and pers_mean) else None,
        "persistent_vs_tightly_coupled_diff_ms": round(pers_mean - tc_mean, 2) if (pers_mean and tc_mean) else None,
        "notes": (
            "Condition A (Tightly Coupled) executes directly in-memory with zero IPC. "
            "Condition B (MCP Process-per-Call) spawns 4 new Python subprocesses per workflow. "
            "Condition C (Persistent MCP) reuses 4 running FastMCP processes across all workflows via stdio, "
            "isolating IPC and protocol latency from process creation and bootstrap."
        )
    }

    return summary


async def execute_benchmark_async(
    iterations: int = 30,
    warmup_count: int = 10,
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Run controlled benchmark across all three architectures."""
    output_dir = output_dir or (ROOT_DIR / "experiments" / "persistent_mcp")
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_results_file = output_dir / "raw_results.jsonl"
    summary_file = output_dir / "summary.json"

    records: List[Dict[str, Any]] = []
    test_inputs = [
        ("Samsung TV", "electronics"),
        ("Dell XPS Laptop", "electronics"),
        ("Apple iPhone 15", "electronics")
    ]

    mock_paths = {
        "enricher": ROOT_DIR / "servers" / "mock-deterministic" / "enricher_server.py",
        "forecasting": ROOT_DIR / "servers" / "forecasting-replacement" / "server.py",
        "replenishment": ROOT_DIR / "servers" / "mock-deterministic" / "replenishment_server.py",
        "pricing": ROOT_DIR / "servers" / "mock-deterministic" / "pricing_server.py"
    }

    print("\n" + "=" * 70)
    print("🚀 STARTING TASK 06: PERSISTENT MCP & LIFECYCLE BENCHMARK")
    print("=" * 70)
    print(f"Repetitions per architecture: {iterations}")
    print(f"Warm-up runs per architecture: {warmup_count}")

    # -------------------------------------------------------------
    # CONDITION A: Tightly Coupled Baseline
    # -------------------------------------------------------------
    print("\n--- Running Condition A: Tightly Coupled Baseline ---")
    # Warmups
    for i in range(warmup_count):
        prod, cat = test_inputs[i % len(test_inputs)]
        res = run_deterministic_tightly_coupled(prod)
        print(f"  [WARMUP {i+1}/{warmup_count}] TC: {prod} -> {res['status']} ({res['total_duration_ms']} ms)")

    # Measured
    for i in range(iterations):
        prod, cat = test_inputs[i % len(test_inputs)]
        run_id = f"tc-run-{uuid.uuid4().hex[:8]}"
        res = run_deterministic_tightly_coupled(prod)
        s_durations = {sc["service_name"]: sc["duration_ms"] for sc in res.get("service_calls", [])}
        record = {
            "run_id": run_id,
            "architecture": "tightly_coupled",
            "condition": "deterministic_local",
            "input_category": cat,
            "input_product": prod,
            "warmup": False,
            "start_time": res["start_time"],
            "end_time": res["end_time"],
            "total_duration_ms": res["total_duration_ms"],
            "service_durations_ms": s_durations,
            "workflow_status": res["status"],
            "completed_steps": res["completed_steps"],
            "failed_steps": res["failed_steps"],
            "errors": res["errors"],
            "external_api_used": False
        }
        records.append(record)
        print(f"  [{i+1}/{iterations}] TC: {prod} -> {res['status']} ({res['total_duration_ms']} ms)")

    # -------------------------------------------------------------
    # CONDITION B: MCP Process-per-Call
    # -------------------------------------------------------------
    print("\n--- Running Condition B: MCP Process-per-Call ---")
    # Warmups
    for i in range(warmup_count):
        prod, cat = test_inputs[i % len(test_inputs)]
        res = await run_deterministic_mcp_process_per_call(prod)
        print(f"  [WARMUP {i+1}/{warmup_count}] MCP (PPC): {prod} -> {res['status']} ({res['total_duration_ms']} ms)")

    # Measured
    for i in range(iterations):
        prod, cat = test_inputs[i % len(test_inputs)]
        run_id = f"mcp-ppc-run-{uuid.uuid4().hex[:8]}"
        res = await run_deterministic_mcp_process_per_call(prod)
        s_durations = {sc["service_name"]: sc["duration_ms"] for sc in res.get("service_calls", [])}
        record = {
            "run_id": run_id,
            "architecture": "mcp_process_per_call",
            "condition": "deterministic_local",
            "input_category": cat,
            "input_product": prod,
            "warmup": False,
            "start_time": res["start_time"],
            "end_time": res["end_time"],
            "total_duration_ms": res["total_duration_ms"],
            "service_durations_ms": s_durations,
            "workflow_status": res["status"],
            "completed_steps": res["completed_steps"],
            "failed_steps": res["failed_steps"],
            "errors": res["errors"],
            "external_api_used": False
        }
        records.append(record)
        print(f"  [{i+1}/{iterations}] MCP (PPC): {prod} -> {res['status']} ({res['total_duration_ms']} ms)")

    # -------------------------------------------------------------
    # CONDITION C: Persistent MCP Process Pool
    # -------------------------------------------------------------
    print("\n--- Running Condition C: Persistent MCP Process Pool ---")
    pool = PersistentMCPSessionPool(server_paths=mock_paths)
    startup_timings = await pool.start()
    print(f"  [POOL] All 4 servers started. Total startup: {startup_timings.get('_total_pool_startup_ms')} ms")

    try:
        client = PersistentRetailOpsClient(pool)
        # Warmups
        for i in range(warmup_count):
            prod, cat = test_inputs[i % len(test_inputs)]
            res = await client.run_full_workflow(prod)
            print(f"  [WARMUP {i+1}/{warmup_count}] Persistent MCP: {prod} -> {res['status']} ({res['total_duration_ms']} ms)")

        # Measured
        for i in range(iterations):
            prod, cat = test_inputs[i % len(test_inputs)]
            run_id = f"pers-mcp-run-{uuid.uuid4().hex[:8]}"
            res = await client.run_full_workflow(prod)
            s_durations = {sc["service_name"]: sc["duration_ms"] for sc in res.get("service_calls", [])}
            record = {
                "run_id": run_id,
                "architecture": "persistent_mcp",
                "condition": "deterministic_local",
                "input_category": cat,
                "input_product": prod,
                "warmup": False,
                "start_time": res["start_time"],
                "end_time": res["end_time"],
                "total_duration_ms": res["total_duration_ms"],
                "service_durations_ms": s_durations,
                "workflow_status": res["status"],
                "completed_steps": res["completed_steps"],
                "failed_steps": res["failed_steps"],
                "errors": res["errors"],
                "external_api_used": False
            }
            records.append(record)
            print(f"  [{i+1}/{iterations}] Persistent MCP: {prod} -> {res['status']} ({res['total_duration_ms']} ms)")
    finally:
        shutdown_ms = await pool.close()
        print(f"  [POOL] All 4 servers closed cleanly. Shutdown: {shutdown_ms} ms")

    # Compute summary
    summary = compute_benchmark_summary(records)
    summary["lifecycle_breakdown"] = {
        "pool_startup_timings": startup_timings,
        "pool_shutdown_ms": shutdown_ms
    }

    # Write output files
    with open(raw_results_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n✅ Raw records written to: {raw_results_file}")
    print(f"✅ Summary written to: {summary_file}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Run Task 06 Persistent MCP Benchmark")
    parser.add_argument("--iterations", type=int, default=30, help="Measured repetitions per architecture")
    parser.add_argument("--warmup", type=int, default=10, help="Warm-up repetitions per architecture")
    args = parser.parse_args()

    asyncio.run(execute_benchmark_async(
        iterations=args.iterations,
        warmup_count=args.warmup
    ))


if __name__ == "__main__":
    main()
