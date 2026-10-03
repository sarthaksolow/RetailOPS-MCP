"""
Execution Script for Step 8: RetailOps M5 Operational Evaluation.
Runs both RetailOps MCP Decision Provider and Fixed-Threshold Baseline
across all 5 frozen scenarios and 5 representative M5 series (50 simulation runs).
Generates experiments/m5_operational/retailops_results.json.
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import numpy as np

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from experiments.m5_operational.scenarios import SCENARIOS, ScenarioParameters
from experiments.m5_operational.decision_provider import (
    BaseDecisionProvider,
    FixedThresholdDecisionProvider,
    RetailOpsDecisionProvider,
)
from experiments.m5_operational.simulator import InventorySimulator, SimulationResults


def run_full_evaluation() -> Dict[str, Any]:
    series_path = ROOT_DIR / "data" / "m5" / "processed" / "m5_evaluation_series.json"
    if not series_path.exists():
        raise FileNotFoundError(f"Processed M5 series not found at {series_path}")

    with open(series_path, "r", encoding="utf-8") as f:
        series_dict = json.load(f)

    providers: List[BaseDecisionProvider] = [
        RetailOpsDecisionProvider(),
        FixedThresholdDecisionProvider(safety_factor=1.5)
    ]

    all_results: Dict[str, Any] = {
        "metadata": {
            "evaluation_step": "Step 8 - RetailOps M5 Operational Evaluation",
            "protocol_version": "PROTOCOL-EXP-FROZEN-V1",
            "date": "2026-10-03",
            "horizon_days": 28,
            "random_seed": 42,
            "series_count": len(series_dict),
            "scenario_count": len(SCENARIOS),
            "total_runs_per_provider": len(series_dict) * len(SCENARIOS),
            "series_evaluated": list(series_dict.keys()),
            "scenarios_evaluated": list(SCENARIOS.keys())
        },
        "providers": {},
        "comparison": {},
        "verification": {
            "all_conservation_passed": True,
            "zero_constraint_violations": True,
            "audit_trail": []
        }
    }

    raw_runs: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for provider in providers:
        p_id = provider.provider_id
        raw_runs[p_id] = {}
        all_results["providers"][p_id] = {
            "provider_id": p_id,
            "scenarios": {},
            "overall_summary": {}
        }

        all_p_stockout = []
        all_p_service = []
        all_p_holding = []
        all_p_order = []
        all_p_cost = []
        all_p_demand = 0
        all_p_fulfilled = 0
        all_p_lost_sales = 0
        all_p_ordered_units = 0
        all_p_violations = 0

        for scen_id, scenario in SCENARIOS.items():
            raw_runs[p_id][scen_id] = {}
            sim = InventorySimulator(scenario)

            scen_stockout = []
            scen_service = []
            scen_holding = []
            scen_order = []
            scen_cost = []
            scen_demand = 0
            scen_fulfilled = 0
            scen_lost_sales = 0
            scen_ordered_units = 0
            scen_violations = 0
            series_runs = {}

            for s_id, s_data in series_dict.items():
                res: SimulationResults = sim.run_simulation(s_data, provider)

                # Inventory Conservation Audit
                init_inv = res.daily_trace[0].starting_inventory
                total_recv = sum(l.arrivals for l in res.daily_trace)
                total_ful = res.total_fulfilled
                end_inv = res.daily_trace[-1].ending_inventory
                expected_end = init_inv + total_recv - total_ful
                balance_ok = (end_inv == expected_end)
                if not balance_ok:
                    all_results["verification"]["all_conservation_passed"] = False

                if res.constraint_violations_count > 0:
                    all_results["verification"]["zero_constraint_violations"] = False

                all_results["verification"]["audit_trail"].append({
                    "provider": p_id,
                    "scenario": scen_id,
                    "series": s_id,
                    "initial_inventory": init_inv,
                    "total_received": total_recv,
                    "total_fulfilled": total_ful,
                    "ending_inventory": end_inv,
                    "expected_ending_inventory": expected_end,
                    "conservation_satisfied": balance_ok,
                    "constraint_violations": res.constraint_violations_count
                })

                order_count = sum(1 for l in res.daily_trace if l.order_placed > 0)

                run_summary = {
                    "series_id": s_id,
                    "stockout_rate_pct": res.stockout_rate_pct,
                    "service_level_pct": res.service_level_pct,
                    "total_holding_cost": res.total_holding_cost,
                    "total_replenishment_cost": res.total_replenishment_cost,
                    "total_cost": res.total_cost,
                    "constraint_violations_count": res.constraint_violations_count,
                    "total_demand": res.total_demand,
                    "total_fulfilled": res.total_fulfilled,
                    "total_lost_sales": res.total_lost_sales,
                    "total_ordered": res.total_ordered,
                    "order_count": order_count,
                    "initial_inventory": init_inv,
                    "ending_inventory": end_inv,
                    "total_received": total_recv,
                    "conservation_satisfied": balance_ok
                }
                series_runs[s_id] = run_summary
                raw_runs[p_id][scen_id][s_id] = run_summary

                scen_stockout.append(res.stockout_rate_pct)
                scen_service.append(res.service_level_pct)
                scen_holding.append(res.total_holding_cost)
                scen_order.append(res.total_replenishment_cost)
                scen_cost.append(res.total_cost)
                scen_demand += res.total_demand
                scen_fulfilled += res.total_fulfilled
                scen_lost_sales += res.total_lost_sales
                scen_ordered_units += res.total_ordered
                scen_violations += res.constraint_violations_count

            all_results["providers"][p_id]["scenarios"][scen_id] = {
                "scenario_name": scenario.scenario_name,
                "description": scenario.description,
                "mean_stockout_rate_pct": round(float(np.mean(scen_stockout)), 2),
                "mean_service_level_pct": round(float(np.mean(scen_service)), 2),
                "mean_holding_cost": round(float(np.mean(scen_holding)), 2),
                "mean_replenishment_cost": round(float(np.mean(scen_order)), 2),
                "mean_total_cost": round(float(np.mean(scen_cost)), 2),
                "total_demand": scen_demand,
                "total_fulfilled": scen_fulfilled,
                "total_lost_sales": scen_lost_sales,
                "total_ordered_units": scen_ordered_units,
                "total_constraint_violations": scen_violations,
                "series_results": series_runs
            }

            all_p_stockout.extend(scen_stockout)
            all_p_service.extend(scen_service)
            all_p_holding.extend(scen_holding)
            all_p_order.extend(scen_order)
            all_p_cost.extend(scen_cost)
            all_p_demand += scen_demand
            all_p_fulfilled += scen_fulfilled
            all_p_lost_sales += scen_lost_sales
            all_p_ordered_units += scen_ordered_units
            all_p_violations += scen_violations

        all_results["providers"][p_id]["overall_summary"] = {
            "mean_stockout_rate_pct": round(float(np.mean(all_p_stockout)), 2),
            "std_stockout_rate_pct": round(float(np.std(all_p_stockout)), 2),
            "mean_service_level_pct": round(float(np.mean(all_p_service)), 2),
            "std_service_level_pct": round(float(np.std(all_p_service)), 2),
            "mean_holding_cost": round(float(np.mean(all_p_holding)), 2),
            "mean_replenishment_cost": round(float(np.mean(all_p_order)), 2),
            "mean_total_cost": round(float(np.mean(all_p_cost)), 2),
            "std_total_cost": round(float(np.std(all_p_cost)), 2),
            "total_demand": all_p_demand,
            "total_fulfilled": all_p_fulfilled,
            "total_lost_sales": all_p_lost_sales,
            "total_ordered_units": all_p_ordered_units,
            "total_constraint_violations": all_p_violations
        }

    # Comparative Analysis (RetailOps vs Baseline)
    ret_id = "retailops_mcp"
    base_id = "fixed_threshold_baseline"
    comparison_by_scen = {}

    for scen_id in SCENARIOS.keys():
        ret_scen = all_results["providers"][ret_id]["scenarios"][scen_id]
        base_scen = all_results["providers"][base_id]["scenarios"][scen_id]

        stockout_diff = round(ret_scen["mean_stockout_rate_pct"] - base_scen["mean_stockout_rate_pct"], 2)
        service_diff = round(ret_scen["mean_service_level_pct"] - base_scen["mean_service_level_pct"], 2)
        cost_diff = round(ret_scen["mean_total_cost"] - base_scen["mean_total_cost"], 2)
        cost_ratio = round(ret_scen["mean_total_cost"] / base_scen["mean_total_cost"], 3) if base_scen["mean_total_cost"] > 0 else 1.0

        comparison_by_scen[scen_id] = {
            "scenario_name": ret_scen["scenario_name"],
            "retailops_stockout_pct": ret_scen["mean_stockout_rate_pct"],
            "baseline_stockout_pct": base_scen["mean_stockout_rate_pct"],
            "stockout_rate_delta_pct": stockout_diff,
            "retailops_service_pct": ret_scen["mean_service_level_pct"],
            "baseline_service_pct": base_scen["mean_service_level_pct"],
            "service_level_delta_pct": service_diff,
            "retailops_total_cost": ret_scen["mean_total_cost"],
            "baseline_total_cost": base_scen["mean_total_cost"],
            "cost_delta": cost_diff,
            "cost_ratio_retailops_to_baseline": cost_ratio,
            "lost_sales_reduction_units": base_scen["total_lost_sales"] - ret_scen["total_lost_sales"]
        }

    ret_ov = all_results["providers"][ret_id]["overall_summary"]
    base_ov = all_results["providers"][base_id]["overall_summary"]

    all_results["comparison"] = {
        "per_scenario": comparison_by_scen,
        "overall": {
            "retailops_overall_stockout_pct": ret_ov["mean_stockout_rate_pct"],
            "baseline_overall_stockout_pct": base_ov["mean_stockout_rate_pct"],
            "overall_stockout_reduction_pct_pts": round(base_ov["mean_stockout_rate_pct"] - ret_ov["mean_stockout_rate_pct"], 2),
            "retailops_overall_service_pct": ret_ov["mean_service_level_pct"],
            "baseline_overall_service_pct": base_ov["mean_service_level_pct"],
            "overall_service_gain_pct_pts": round(ret_ov["mean_service_level_pct"] - base_ov["mean_service_level_pct"], 2),
            "retailops_mean_cost": ret_ov["mean_total_cost"],
            "baseline_mean_cost": base_ov["mean_total_cost"],
            "overall_cost_delta": round(ret_ov["mean_total_cost"] - base_ov["mean_total_cost"], 2),
            "total_lost_sales_retailops": ret_ov["total_lost_sales"],
            "total_lost_sales_baseline": base_ov["total_lost_sales"],
            "net_lost_sales_prevented_units": base_ov["total_lost_sales"] - ret_ov["total_lost_sales"]
        }
    }

    out_file = ROOT_DIR / "experiments" / "m5_operational" / "retailops_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print(f"Results successfully saved to {out_file}")
    return all_results


if __name__ == "__main__":
    run_full_evaluation()
