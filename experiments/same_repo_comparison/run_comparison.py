"""
Execution Script for Step 10: Same-Repository Research Architecture Comparison.
Evaluates four distinct decision orchestration architectures:
1. RetailOps MCP (retailops_mcp)
2. Flowr Coordinator Pattern (flowr_coordinator)
3. WorkflowLLM Generative Pattern (workflowllm_generative)
4. Agentic Inventory Replenishment Pattern (agentic_replenishment)
(Plus Fixed-Threshold Baseline as reference benchmark)

Across all 5 frozen M5 operational scenarios and 5 store-item series (125 total runs).
Exports results to experiments/same_repo_comparison/results.json.
"""
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from experiments.m5_operational.scenarios import SCENARIOS, ScenarioParameters
from experiments.m5_operational.decision_provider import (
    BaseDecisionProvider,
    RetailOpsDecisionProvider,
    FixedThresholdDecisionProvider,
)
from experiments.same_repo_comparison import (
    FlowrCoordinatorDecisionProvider,
    WorkflowLLMDecisionProvider,
    AgenticReplenishmentDecisionProvider,
)
from experiments.m5_operational.simulator import InventorySimulator, SimulationResults


def count_file_loc(path: Path) -> int:
    """Counts non-empty lines in a file."""
    if not path.exists():
        return 0
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def run_architecture_comparison() -> Dict[str, Any]:
    series_path = ROOT_DIR / "data" / "m5" / "processed" / "m5_evaluation_series.json"
    if not series_path.exists():
        raise FileNotFoundError(f"M5 series file missing at {series_path}")

    with open(series_path, "r", encoding="utf-8") as f:
        series_dict = json.load(f)

    # 4 Architectures + 1 Benchmark Reference
    providers: List[BaseDecisionProvider] = [
        RetailOpsDecisionProvider(),
        FlowrCoordinatorDecisionProvider(),
        WorkflowLLMDecisionProvider(),
        AgenticReplenishmentDecisionProvider(),
        FixedThresholdDecisionProvider(safety_factor=1.5)
    ]

    # Measure implementation & modularity metrics
    modularity_metrics = {
        "flowr_coordinator": {
            "implementation_files_count": 1,
            "implementation_files": ["experiments/same_repo_comparison/flowr_coordinator/coordinator.py"],
            "implementation_loc": count_file_loc(ROOT_DIR / "experiments" / "same_repo_comparison" / "flowr_coordinator" / "coordinator.py"),
            "existing_retailops_files_modified": 0,
            "external_dependencies": ["None (standard library & common decision provider)"],
            "architecture_pattern": "Centralized Reasoning Coordinator with Modular Tool Functions",
            "structural_components": [
                "FlowrCoordinatorDecisionProvider",
                "FlowrDomainTools (monitor_inventory, forecast_demand, plan_procurement, coordinate_supplier)"
            ]
        },
        "workflowllm_generative": {
            "implementation_files_count": 1,
            "implementation_files": ["experiments/same_repo_comparison/workflowllm_generative/generative_workflow.py"],
            "implementation_loc": count_file_loc(ROOT_DIR / "experiments" / "same_repo_comparison" / "workflowllm_generative" / "generative_workflow.py"),
            "existing_retailops_files_modified": 0,
            "external_dependencies": ["None (standard library & common decision provider)"],
            "architecture_pattern": "Generative Plan-then-Execute Workflow with Dynamic Parameter Binding",
            "structural_components": [
                "WorkflowPlanStep Schema",
                "WorkflowLLMPlanner (Phase 1 plan synthesis)",
                "WorkflowLLMExecutor (Phase 2 step execution & parameter binding)",
                "WorkflowLLMDecisionProvider"
            ]
        },
        "agentic_replenishment": {
            "implementation_files_count": 1,
            "implementation_files": ["experiments/same_repo_comparison/agentic_replenishment/direct_agent.py"],
            "implementation_loc": count_file_loc(ROOT_DIR / "experiments" / "same_repo_comparison" / "agentic_replenishment" / "direct_agent.py"),
            "existing_retailops_files_modified": 0,
            "external_dependencies": ["None (standard library & common decision provider)"],
            "architecture_pattern": "Single-Domain Autonomous Direct Replenishment Agent",
            "structural_components": [
                "AgenticReplenishmentDecisionProvider (Direct perception-action inventory loop)"
            ]
        },
        "retailops_mcp": {
            "implementation_files_count": 5,
            "implementation_files": [
                "servers/catalog-enricher/server.py",
                "servers/forecasting/server.py",
                "servers/replenishment/server.py",
                "servers/pricing-strategy/server.py",
                "experiments/m5_operational/decision_provider.py (RetailOps adapter)"
            ],
            "implementation_loc": 94,  # Adapter LOC connecting to replenishment pipeline
            "existing_retailops_files_modified": 0,
            "external_dependencies": ["mcp", "fastmcp", "langgraph", "openai", "pydantic"],
            "architecture_pattern": "Multi-Process MCP STDIO Subprocesses Coordinated by Compiled LangGraph StateGraph",
            "structural_components": [
                "FastMCP Servers (catalog, forecast, replenishment, pricing)",
                "LangGraph StateGraph DAG Workflow",
                "RetailOpsDecisionProvider Adapter"
            ]
        },
        "fixed_threshold_baseline": {
            "implementation_files_count": 1,
            "implementation_files": ["experiments/m5_operational/decision_provider.py"],
            "implementation_loc": 53,
            "existing_retailops_files_modified": 0,
            "external_dependencies": ["None"],
            "architecture_pattern": "Continuous Review (s, S) Mathematical Heuristic",
            "structural_components": ["FixedThresholdDecisionProvider"]
        }
    }

    full_results: Dict[str, Any] = {
        "metadata": {
            "evaluation_phase": "Step 10 — Same-Repository Architecture Comparison",
            "protocol_reference": "PROTOCOL-EXP-FROZEN-V1",
            "date": "2026-10-03",
            "horizon_days": 28,
            "random_seed": 42,
            "python_version": sys.version.split()[0],
            "series_evaluated": list(series_dict.keys()),
            "scenarios_evaluated": list(SCENARIOS.keys()),
            "architectures_evaluated": [p.provider_id for p in providers]
        },
        "modularity_and_implementation": modularity_metrics,
        "architectures": {},
        "per_scenario_comparison": {},
        "overall_comparison": {},
        "verification": {
            "all_conservation_passed": True,
            "zero_constraint_violations": True,
            "total_audit_records": 0,
            "audit_trail": []
        }
    }

    for provider in providers:
        p_id = provider.provider_id
        t_start = time.perf_counter()

        all_stockout = []
        all_service = []
        all_holding = []
        all_order_cost = []
        all_total_cost = []
        all_demand = 0
        all_fulfilled = 0
        all_lost_sales = 0
        all_ordered = 0
        all_violations = 0

        scenarios_data = {}

        for scen_id, scenario in SCENARIOS.items():
            sim = InventorySimulator(scenario)

            scen_stockout = []
            scen_service = []
            scen_holding = []
            scen_order_cost = []
            scen_total_cost = []
            scen_demand = 0
            scen_fulfilled = 0
            scen_lost_sales = 0
            scen_ordered = 0
            scen_violations = 0
            series_runs = {}

            for s_id, s_data in series_dict.items():
                res = sim.run_simulation(s_data, provider)

                # Inventory Conservation Audit
                init_inv = res.daily_trace[0].starting_inventory
                recv = sum(l.arrivals for l in res.daily_trace)
                ful = res.total_fulfilled
                end_inv = res.daily_trace[-1].ending_inventory
                expected_end = init_inv + recv - ful
                conservation_ok = (end_inv == expected_end)
                if not conservation_ok:
                    full_results["verification"]["all_conservation_passed"] = False

                if res.constraint_violations_count > 0:
                    full_results["verification"]["zero_constraint_violations"] = False

                full_results["verification"]["total_audit_records"] += 1
                full_results["verification"]["audit_trail"].append({
                    "provider": p_id,
                    "scenario": scen_id,
                    "series": s_id,
                    "initial_inventory": init_inv,
                    "total_received": recv,
                    "total_fulfilled": ful,
                    "ending_inventory": end_inv,
                    "conservation_satisfied": conservation_ok,
                    "constraint_violations": res.constraint_violations_count
                })

                order_count = sum(1 for l in res.daily_trace if l.order_placed > 0)

                series_runs[s_id] = {
                    "series_id": s_id,
                    "stockout_rate_pct": res.stockout_rate_pct,
                    "service_level_pct": res.service_level_pct,
                    "holding_cost": res.total_holding_cost,
                    "replenishment_cost": res.total_replenishment_cost,
                    "total_cost": res.total_cost,
                    "total_demand": res.total_demand,
                    "total_fulfilled": res.total_fulfilled,
                    "lost_sales": res.total_lost_sales,
                    "total_ordered": res.total_ordered,
                    "order_count": order_count,
                    "initial_inventory": init_inv,
                    "ending_inventory": end_inv,
                    "conservation_satisfied": conservation_ok,
                    "constraint_violations": res.constraint_violations_count
                }

                scen_stockout.append(res.stockout_rate_pct)
                scen_service.append(res.service_level_pct)
                scen_holding.append(res.total_holding_cost)
                scen_order_cost.append(res.total_replenishment_cost)
                scen_total_cost.append(res.total_cost)
                scen_demand += res.total_demand
                scen_fulfilled += res.total_fulfilled
                scen_lost_sales += res.total_lost_sales
                scen_ordered += res.total_ordered
                scen_violations += res.constraint_violations_count

            scenarios_data[scen_id] = {
                "scenario_name": scenario.scenario_name,
                "mean_stockout_rate_pct": round(float(np.mean(scen_stockout)), 2),
                "mean_service_level_pct": round(float(np.mean(scen_service)), 2),
                "mean_holding_cost": round(float(np.mean(scen_holding)), 2),
                "mean_replenishment_cost": round(float(np.mean(scen_order_cost)), 2),
                "mean_total_cost": round(float(np.mean(scen_total_cost)), 2),
                "total_demand": scen_demand,
                "total_fulfilled": scen_fulfilled,
                "total_lost_sales": scen_lost_sales,
                "total_ordered_units": scen_ordered,
                "total_constraint_violations": scen_violations,
                "series_results": series_runs
            }

            all_stockout.extend(scen_stockout)
            all_service.extend(scen_service)
            all_holding.extend(scen_holding)
            all_order_cost.extend(scen_order_cost)
            all_total_cost.extend(scen_total_cost)
            all_demand += scen_demand
            all_fulfilled += scen_fulfilled
            all_lost_sales += scen_lost_sales
            all_ordered += scen_ordered
            all_violations += scen_violations

        t_elapsed = round((time.perf_counter() - t_start) * 1000, 2)

        full_results["architectures"][p_id] = {
            "provider_id": p_id,
            "architecture_pattern": modularity_metrics[p_id]["architecture_pattern"],
            "total_execution_time_ms": t_elapsed,
            "mean_execution_time_per_simulation_ms": round(t_elapsed / 25, 2),
            "overall_summary": {
                "mean_stockout_rate_pct": round(float(np.mean(all_stockout)), 2),
                "std_stockout_rate_pct": round(float(np.std(all_stockout)), 2),
                "mean_service_level_pct": round(float(np.mean(all_service)), 2),
                "std_service_level_pct": round(float(np.std(all_service)), 2),
                "mean_holding_cost": round(float(np.mean(all_holding)), 2),
                "mean_replenishment_cost": round(float(np.mean(all_order_cost)), 2),
                "mean_total_cost": round(float(np.mean(all_total_cost)), 2),
                "std_total_cost": round(float(np.std(all_total_cost)), 2),
                "total_demand": all_demand,
                "total_fulfilled": all_fulfilled,
                "total_lost_sales": all_lost_sales,
                "total_ordered_units": all_ordered,
                "total_constraint_violations": all_violations
            },
            "scenarios": scenarios_data
        }

    # Consolidated Per-Scenario Matrix across all 4 architectures + baseline
    for scen_id in SCENARIOS.keys():
        scen_comp = {}
        for provider in providers:
            p_id = provider.provider_id
            s_data = full_results["architectures"][p_id]["scenarios"][scen_id]
            scen_comp[p_id] = {
                "mean_stockout_rate_pct": s_data["mean_stockout_rate_pct"],
                "mean_service_level_pct": s_data["mean_service_level_pct"],
                "mean_total_cost": s_data["mean_total_cost"],
                "total_lost_sales": s_data["total_lost_sales"],
                "total_ordered_units": s_data["total_ordered_units"]
            }
        full_results["per_scenario_comparison"][scen_id] = {
            "scenario_name": SCENARIOS[scen_id].scenario_name,
            "providers": scen_comp
        }

    # Overall Cross-Architecture Comparison Summary
    overall_comp = {}
    for provider in providers:
        p_id = provider.provider_id
        ov = full_results["architectures"][p_id]["overall_summary"]
        overall_comp[p_id] = {
            "architecture_pattern": modularity_metrics[p_id]["architecture_pattern"],
            "mean_stockout_rate_pct": ov["mean_stockout_rate_pct"],
            "mean_service_level_pct": ov["mean_service_level_pct"],
            "mean_total_cost": ov["mean_total_cost"],
            "total_fulfilled_units": ov["total_fulfilled"],
            "total_lost_sales_units": ov["total_lost_sales"],
            "total_ordered_units": ov["total_ordered_units"],
            "total_constraint_violations": ov["total_constraint_violations"],
            "total_runtime_ms": full_results["architectures"][p_id]["total_execution_time_ms"],
            "implementation_loc": modularity_metrics[p_id]["implementation_loc"]
        }
    full_results["overall_comparison"] = overall_comp

    out_file = ROOT_DIR / "experiments" / "same_repo_comparison" / "results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_results, f, indent=2)

    print(f"Results successfully saved to {out_file}")
    return full_results


if __name__ == "__main__":
    run_architecture_comparison()
