"""
Execution Script for Step 11: Human-in-the-Loop (HITL) Operational Comparison.
Evaluates:
1. Mode A: Fully Autonomous Operation (retailops_autonomous)
2. Mode B: Human-Supervised Operation with Approval Gate (retailops_human_supervised)

Across all 5 frozen M5 scenarios and 5 store-item series (50 total simulation runs).
Exports results to experiments/hitl_comparison/results.json.
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
from experiments.hitl_comparison.hitl_provider import (
    RetailOpsAutonomousProvider,
    RetailOpsSupervisedProvider
)
from experiments.m5_operational.simulator import InventorySimulator, SimulationResults


def run_hitl_evaluation() -> Dict[str, Any]:
    series_path = ROOT_DIR / "data" / "m5" / "processed" / "m5_evaluation_series.json"
    if not series_path.exists():
        raise FileNotFoundError(f"M5 series file missing at {series_path}")

    with open(series_path, "r", encoding="utf-8") as f:
        series_dict = json.load(f)

    providers = [
        RetailOpsAutonomousProvider(),
        RetailOpsSupervisedProvider(budget_threshold_usd=100.0, simulated_review_latency_seconds=15.0)
    ]

    full_results: Dict[str, Any] = {
        "metadata": {
            "evaluation_phase": "Step 11 — Human-in-the-Loop (HITL) Comparison",
            "protocol_reference": "PROTOCOL-EXP-FROZEN-V1",
            "date": "2026-10-03",
            "horizon_days": 28,
            "random_seed": 42,
            "python_version": sys.version.split()[0],
            "series_evaluated": list(series_dict.keys()),
            "scenarios_evaluated": list(SCENARIOS.keys()),
            "modes_evaluated": ["retailops_autonomous", "retailops_human_supervised"],
            "operator_model": "Deterministic simulated operator policy based on frozen protocol governance criteria"
        },
        "modes": {},
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

        # HITL Specific Metrics
        all_decisions_count = 0
        all_escalations_count = 0
        all_approvals_count = 0
        all_overrides_count = 0
        all_prevented_violations_count = 0
        all_total_latency_seconds = 0.0

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

            scen_decisions = 0
            scen_escalations = 0
            scen_approvals = 0
            scen_overrides = 0
            scen_prevented_violations = 0
            scen_latency = 0.0

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

                # Extract HITL daily metadata from provider
                run_decisions = len(res.daily_trace)
                run_escalations = 0
                run_approvals = 0
                run_overrides = 0
                run_prevented = 0
                run_latency = 0.0

                # Re-query provider metadata via daily simulation log or provider
                for day_log in res.daily_trace:
                    # In daily trace, decision rationale captures operator action
                    rat = day_log.decision_rationale
                    if "[Supervised Mode]" in rat:
                        if "Action: OVERRIDE" in rat:
                            run_overrides += 1
                            run_escalations += 1
                            run_latency += 15.0
                            run_prevented += 1
                        elif "Action: APPROVE" in rat:
                            run_approvals += 1
                            if "Latency: 15.0s" in rat:
                                run_escalations += 1
                                run_latency += 15.0
                    else:
                        # Autonomous mode: all decisions auto-approved with zero latency
                        run_approvals += 1

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
                    "constraint_violations": res.constraint_violations_count,
                    "decisions_count": run_decisions,
                    "escalations_count": run_escalations,
                    "approvals_count": run_approvals,
                    "overrides_count": run_overrides,
                    "prevented_violations_count": run_prevented,
                    "total_latency_seconds": round(run_latency, 1)
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

                scen_decisions += run_decisions
                scen_escalations += run_escalations
                scen_approvals += run_approvals
                scen_overrides += run_overrides
                scen_prevented_violations += run_prevented
                scen_latency += run_latency

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
                "decisions_count": scen_decisions,
                "escalations_count": scen_escalations,
                "approvals_count": scen_approvals,
                "overrides_count": scen_overrides,
                "prevented_violations_count": scen_prevented_violations,
                "approval_rate_pct": round((scen_approvals / scen_decisions) * 100, 2) if scen_decisions > 0 else 100.0,
                "override_rate_pct": round((scen_overrides / scen_decisions) * 100, 2) if scen_decisions > 0 else 0.0,
                "total_latency_seconds": round(scen_latency, 1),
                "mean_latency_per_decision_seconds": round(scen_latency / scen_decisions, 2) if scen_decisions > 0 else 0.0,
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

            all_decisions_count += scen_decisions
            all_escalations_count += scen_escalations
            all_approvals_count += scen_approvals
            all_overrides_count += scen_overrides
            all_prevented_violations_count += scen_prevented_violations
            all_total_latency_seconds += scen_latency

        t_elapsed = round((time.perf_counter() - t_start) * 1000, 2)

        full_results["modes"][p_id] = {
            "provider_id": p_id,
            "mode_name": "Autonomous" if "autonomous" in p_id else "Human-Supervised",
            "total_execution_time_ms": t_elapsed,
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
                "total_constraint_violations": all_violations,
                "total_decisions_evaluated": all_decisions_count,
                "total_escalations": all_escalations_count,
                "total_approvals": all_approvals_count,
                "total_overrides": all_overrides_count,
                "total_prevented_policy_violations": all_prevented_violations_count,
                "approval_rate_pct": round((all_approvals_count / all_decisions_count) * 100, 2) if all_decisions_count > 0 else 100.0,
                "override_rate_pct": round((all_overrides_count / all_decisions_count) * 100, 2) if all_decisions_count > 0 else 0.0,
                "total_simulated_latency_seconds": round(all_total_latency_seconds, 1),
                "mean_latency_per_decision_seconds": round(all_total_latency_seconds / all_decisions_count, 2) if all_decisions_count > 0 else 0.0
            },
            "scenarios": scenarios_data
        }

    # Consolidated Per-Scenario Comparison
    for scen_id in SCENARIOS.keys():
        auto_scen = full_results["modes"]["retailops_autonomous"]["scenarios"][scen_id]
        sup_scen = full_results["modes"]["retailops_human_supervised"]["scenarios"][scen_id]

        full_results["per_scenario_comparison"][scen_id] = {
            "scenario_name": SCENARIOS[scen_id].scenario_name,
            "autonomous": {
                "stockout_rate_pct": auto_scen["mean_stockout_rate_pct"],
                "service_level_pct": auto_scen["mean_service_level_pct"],
                "mean_total_cost": auto_scen["mean_total_cost"],
                "lost_sales": auto_scen["total_lost_sales"],
                "units_ordered": auto_scen["total_ordered_units"],
                "escalations": auto_scen["escalations_count"],
                "overrides": auto_scen["overrides_count"],
                "approval_rate_pct": auto_scen["approval_rate_pct"]
            },
            "supervised": {
                "stockout_rate_pct": sup_scen["mean_stockout_rate_pct"],
                "service_level_pct": sup_scen["mean_service_level_pct"],
                "mean_total_cost": sup_scen["mean_total_cost"],
                "lost_sales": sup_scen["total_lost_sales"],
                "units_ordered": sup_scen["total_ordered_units"],
                "escalations": sup_scen["escalations_count"],
                "overrides": sup_scen["overrides_count"],
                "approval_rate_pct": sup_scen["approval_rate_pct"],
                "prevented_violations": sup_scen["prevented_violations_count"],
                "mean_latency_seconds": sup_scen["mean_latency_per_decision_seconds"]
            },
            "differences": {
                "stockout_rate_delta_pct": round(sup_scen["mean_stockout_rate_pct"] - auto_scen["mean_stockout_rate_pct"], 2),
                "service_level_delta_pct": round(sup_scen["mean_service_level_pct"] - auto_scen["mean_service_level_pct"], 2),
                "total_cost_delta": round(sup_scen["mean_total_cost"] - auto_scen["mean_total_cost"], 2),
                "lost_sales_delta": sup_scen["total_lost_sales"] - auto_scen["total_lost_sales"],
                "ordered_units_delta": sup_scen["total_ordered_units"] - auto_scen["total_ordered_units"]
            }
        }

    # Overall Mode Comparison
    auto_ov = full_results["modes"]["retailops_autonomous"]["overall_summary"]
    sup_ov = full_results["modes"]["retailops_human_supervised"]["overall_summary"]

    full_results["overall_comparison"] = {
        "autonomous": auto_ov,
        "supervised": sup_ov,
        "deltas_supervised_minus_autonomous": {
            "stockout_rate_delta_pct": round(sup_ov["mean_stockout_rate_pct"] - auto_ov["mean_stockout_rate_pct"], 2),
            "service_level_delta_pct": round(sup_ov["mean_service_level_pct"] - auto_ov["mean_service_level_pct"], 2),
            "total_cost_delta": round(sup_ov["mean_total_cost"] - auto_ov["mean_total_cost"], 2),
            "holding_cost_delta": round(sup_ov["mean_holding_cost"] - auto_ov["mean_holding_cost"], 2),
            "reorder_cost_delta": round(sup_ov["mean_replenishment_cost"] - auto_ov["mean_replenishment_cost"], 2),
            "fulfilled_demand_delta": sup_ov["total_fulfilled"] - auto_ov["total_fulfilled"],
            "lost_sales_delta": sup_ov["total_lost_sales"] - auto_ov["total_lost_sales"],
            "ordered_units_delta": sup_ov["total_ordered_units"] - auto_ov["total_ordered_units"],
            "total_escalations": sup_ov["total_escalations"],
            "total_overrides": sup_ov["total_overrides"],
            "total_prevented_violations": sup_ov["total_prevented_policy_violations"],
            "overall_approval_rate_pct": sup_ov["approval_rate_pct"],
            "overall_override_rate_pct": sup_ov["override_rate_pct"],
            "total_simulated_latency_seconds": sup_ov["total_simulated_latency_seconds"],
            "mean_latency_per_decision_seconds": sup_ov["mean_latency_per_decision_seconds"]
        }
    }

    out_file = ROOT_DIR / "experiments" / "hitl_comparison" / "results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_results, f, indent=2)

    print(f"HITL Results successfully saved to {out_file}")
    return full_results


if __name__ == "__main__":
    run_hitl_evaluation()
