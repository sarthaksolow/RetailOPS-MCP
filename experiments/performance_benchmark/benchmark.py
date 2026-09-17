"""
Controlled Runtime and Orchestration-Overhead Benchmark for RetailOps.
Compares MCP architecture against the Tightly Coupled baseline under:
1. Condition A: Deterministic Local Benchmark (zero external LLMs/APIs, deterministic local calculations)
2. Condition B: End-to-End Production-Like Benchmark (existing production workflow with LLMs/APIs)
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

# Set root dir in Python path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "client"))

from client.orchestrator import RetailOpsClient, MCPServerManager
from baseline.tightly_coupled import TightlyCoupledRetailOps
from baseline.replacement.forecasting_replacement import replacement_direct_get_forecast
from client.telemetry import now_iso


def run_deterministic_tightly_coupled(product: str, days_ahead: int = 30) -> Dict[str, Any]:
    """Execute tightly coupled workflow deterministically in-process."""
    tc = TightlyCoupledRetailOps(forecasting_service=replacement_direct_get_forecast)
    return tc.run_full_workflow(product, days_ahead=days_ahead)


async def run_deterministic_mcp(product: str, days_ahead: int = 30) -> Dict[str, Any]:
    """Execute MCP workflow with local deterministic MCP servers."""
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


async def run_production_mcp(product: str, days_ahead: int = 30) -> Dict[str, Any]:
    """Execute standard production MCP workflow with remote LLM/API calls."""
    # Ensure default server paths
    for k in [
        "RETAILOPS_ENRICHER_SERVER_PATH",
        "RETAILOPS_FORECASTING_SERVER_PATH",
        "RETAILOPS_REPLENISHMENT_SERVER_PATH",
        "RETAILOPS_PRICING_SERVER_PATH"
    ]:
        os.environ.pop(k, None)

    client = RetailOpsClient()
    return await client.run_full_workflow(product, days_ahead=days_ahead)


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


def execute_benchmark(
    condition: str = "deterministic_local",
    iterations: int = 30,
    warmup_count: int = 2,
    output_dir: Optional[Path] = None,
    run_e2e: bool = True
) -> Dict[str, Any]:
    """Run controlled benchmark across both architectures."""
    output_dir = output_dir or (ROOT_DIR / "experiments" / "performance_benchmark")
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_results_file = output_dir / "raw_results.jsonl"
    summary_file = output_dir / "summary.json"

    records = []
    test_inputs = [
        ("Samsung TV", "electronics"),
        ("Dell XPS Laptop", "electronics"),
        ("Apple iPhone 15", "electronics")
    ]

    print(f"\n{'='*70}\n🚀 STARTING CONTROLLED PERFORMANCE BENCHMARK\n{'='*70}")
    print(f"Condition: {condition}")
    print(f"Measured repetitions: {iterations} per architecture")
    print(f"Warm-up runs: {warmup_count} per architecture\n")

    # -------------------------------------------------------------
    # 1. Condition A: Deterministic Tightly Coupled
    # -------------------------------------------------------------
    print(f"--- Running Tightly Coupled (Deterministic) ---")
    for i in range(warmup_count + iterations):
        is_warmup = i < warmup_count
        product, category = test_inputs[i % len(test_inputs)]
        run_id = f"tc-det-{uuid.uuid4().hex[:8]}"
        t_start = time.perf_counter()
        t_start_iso = now_iso()

        status = "unknown"
        completed_steps = []
        failed_steps = []
        errors = []
        service_durations = {}

        try:
            res = run_deterministic_tightly_coupled(product, days_ahead=30)
            status = res.get("status", "unknown")
            completed_steps = res.get("completed_steps", [])
            failed_steps = res.get("failed_steps", [])
            errors = res.get("errors", [])
            for call in res.get("service_calls", []):
                service_durations[call["service_name"]] = call.get("duration_ms", 0)
        except Exception as e:
            status = "failed"
            errors.append(str(e))

        t_end_iso = now_iso()
        total_duration_ms = round((time.perf_counter() - t_start) * 1000, 2)

        record = {
            "run_id": run_id,
            "architecture": "tightly_coupled",
            "condition": "deterministic_local",
            "input_category": category,
            "input_product": product,
            "warmup": is_warmup,
            "start_time": t_start_iso,
            "end_time": t_end_iso,
            "total_duration_ms": total_duration_ms,
            "service_durations_ms": service_durations,
            "workflow_status": status,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "errors": errors,
            "external_api_used": False
        }
        records.append(record)
        prefix = "[WARMUP]" if is_warmup else f"[{i - warmup_count + 1}/{iterations}]"
        print(f"  {prefix} TC: {product} -> {status} ({total_duration_ms:.2f} ms)")

    # -------------------------------------------------------------
    # 2. Condition A: Deterministic MCP
    # -------------------------------------------------------------
    print(f"\n--- Running MCP Architecture (Deterministic Local) ---")
    for i in range(warmup_count + iterations):
        is_warmup = i < warmup_count
        product, category = test_inputs[i % len(test_inputs)]
        run_id = f"mcp-det-{uuid.uuid4().hex[:8]}"
        t_start = time.perf_counter()
        t_start_iso = now_iso()

        status = "unknown"
        completed_steps = []
        failed_steps = []
        errors = []
        service_durations = {}

        try:
            res = asyncio.run(run_deterministic_mcp(product, days_ahead=30))
            status = res.get("status", "unknown")
            completed_steps = res.get("completed_steps", [])
            failed_steps = res.get("failed_steps", [])
            errors = res.get("errors", [])
            for call in res.get("service_calls", []):
                service_durations[call["service_name"]] = call.get("duration_ms", 0)
        except Exception as e:
            status = "failed"
            errors.append(str(e))

        t_end_iso = now_iso()
        total_duration_ms = round((time.perf_counter() - t_start) * 1000, 2)

        record = {
            "run_id": run_id,
            "architecture": "mcp",
            "condition": "deterministic_local",
            "input_category": category,
            "input_product": product,
            "warmup": is_warmup,
            "start_time": t_start_iso,
            "end_time": t_end_iso,
            "total_duration_ms": total_duration_ms,
            "service_durations_ms": service_durations,
            "workflow_status": status,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "errors": errors,
            "external_api_used": False
        }
        records.append(record)
        prefix = "[WARMUP]" if is_warmup else f"[{i - warmup_count + 1}/{iterations}]"
        print(f"  {prefix} MCP (det): {product} -> {status} ({total_duration_ms:.2f} ms)")

    # -------------------------------------------------------------
    # 3. Condition B: End-to-End Production-Like MCP (Optional)
    # -------------------------------------------------------------
    e2e_iterations = 5 if run_e2e else 0
    if run_e2e and os.getenv("OPENROUTER_API_KEY"):
        print(f"\n--- Running MCP Architecture (Condition B: End-to-End Production) ---")
        for i in range(e2e_iterations):
            product, category = test_inputs[i % len(test_inputs)]
            run_id = f"mcp-e2e-{uuid.uuid4().hex[:8]}"
            t_start = time.perf_counter()
            t_start_iso = now_iso()

            status = "unknown"
            completed_steps = []
            failed_steps = []
            errors = []
            service_durations = {}

            try:
                res = asyncio.run(run_production_mcp(product, days_ahead=30))
                status = res.get("status", "unknown")
                completed_steps = res.get("completed_steps", [])
                failed_steps = res.get("failed_steps", [])
                errors = res.get("errors", [])
                for call in res.get("service_calls", []):
                    service_durations[call["service_name"]] = call.get("duration_ms", 0)
            except Exception as e:
                status = "failed"
                errors.append(str(e))

            t_end_iso = now_iso()
            total_duration_ms = round((time.perf_counter() - t_start) * 1000, 2)

            record = {
                "run_id": run_id,
                "architecture": "mcp",
                "condition": "end_to_end",
                "input_category": category,
                "input_product": product,
                "warmup": False,
                "start_time": t_start_iso,
                "end_time": t_end_iso,
                "total_duration_ms": total_duration_ms,
                "service_durations_ms": service_durations,
                "workflow_status": status,
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "errors": errors,
                "external_api_used": True
            }
            records.append(record)
            print(f"  [{i + 1}/{e2e_iterations}] MCP (E2E): {product} -> {status} ({total_duration_ms:.2f} ms)")

    # -------------------------------------------------------------
    # 4. Save Raw Records
    # -------------------------------------------------------------
    with open(raw_results_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"\n✅ Raw records written to: {raw_results_file}")

    # -------------------------------------------------------------
    # 5. Compute Summary Statistics
    # -------------------------------------------------------------
    summary = compute_benchmark_summary(records)
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Summary written to: {summary_file}")

    return summary


def compute_benchmark_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate raw runs into structured metrics."""
    # Filter non-warmup runs
    measured = [r for r in records if not r.get("warmup", False)]

    # Partitions
    tc_det = [r for r in measured if r["architecture"] == "tightly_coupled" and r["condition"] == "deterministic_local"]
    mcp_det = [r for r in measured if r["architecture"] == "mcp" and r["condition"] == "deterministic_local"]
    mcp_e2e = [r for r in measured if r["architecture"] == "mcp" and r["condition"] == "end_to_end"]

    def analyze_group(group: List[Dict[str, Any]]) -> Dict[str, Any]:
        successful = [r for r in group if r["workflow_status"] == "completed"]
        failed = [r for r in group if r["workflow_status"] != "completed"]
        durations = [r["total_duration_ms"] for r in successful]

        service_names = ["Catalog Enricher", "Forecasting", "Replenishment", "Pricing Strategy"]
        per_service = {}
        for s in service_names:
            s_durs = [r["service_durations_ms"].get(s) for r in successful if r["service_durations_ms"].get(s) is not None]
            per_service[s] = calculate_metrics(s_durs)

        return {
            "total_runs": len(group),
            "successful_runs": len(successful),
            "failed_runs": len(failed),
            "completion_rate": round(len(successful) / len(group) * 100, 2) if group else 0.0,
            "overall_runtime_ms": calculate_metrics(durations),
            "per_service_ms": per_service
        }

    tc_det_summary = analyze_group(tc_det)
    mcp_det_summary = analyze_group(mcp_det)
    mcp_e2e_summary = analyze_group(mcp_e2e)

    # Derived comparative metrics for deterministic condition
    derived = {}
    mcp_mean = mcp_det_summary["overall_runtime_ms"]["mean"]
    tc_mean = tc_det_summary["overall_runtime_ms"]["mean"]
    if mcp_mean is not None and tc_mean is not None:
        diff = round(mcp_mean - tc_mean, 2)
        ratio = round(mcp_mean / tc_mean, 2) if tc_mean > 0 else None
        derived["deterministic_runtime_difference_ms"] = diff
        derived["deterministic_runtime_ratio"] = ratio
        derived["notes"] = (
            "The runtime difference includes subprocess creation, Python interpreter startup, "
            "FastMCP initialization, and stdio IPC communication across 4 stages. "
            "It does not isolate pure MCP wire protocol overhead."
        )

    return {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "environment": {
                "os": os.name,
                "platform": sys.platform,
                "python_version": sys.version.split()[0]
            }
        },
        "deterministic_tightly_coupled": tc_det_summary,
        "deterministic_mcp": mcp_det_summary,
        "end_to_end_mcp": mcp_e2e_summary,
        "derived_comparisons": derived
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RetailOps Controlled Performance Benchmark")
    parser.add_argument("--iterations", type=int, default=30, help="Measured repetitions per architecture")
    parser.add_argument("--warmup", type=int, default=2, help="Warm-up repetitions per architecture")
    parser.add_argument("--skip-e2e", action="store_true", help="Skip condition B (end-to-end production)")
    args = parser.parse_args()

    execute_benchmark(
        iterations=args.iterations,
        warmup_count=args.warmup,
        run_e2e=not args.skip_e2e
    )
