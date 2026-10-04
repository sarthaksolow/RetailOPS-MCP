"""
WorkflowLLM Generative Adapter: Statistical Forecasting Replacement.
Adapts the Plan-then-Execute pattern by modifying Phase 1 plan schema
and Phase 2 execution step dispatch to integrate Holt-Winters forecasting.
"""
from typing import Dict, Any, List
from experiments.m5_operational.decision_provider import OperationalDecisionContext
from experiments.same_repo_comparison.workflowllm_generative.generative_workflow import (
    WorkflowPlanStep,
    WorkflowLLMPlanner,
    WorkflowLLMExecutor
)
from experiments.replacement_modularity_comparison.statistical_model import compute_statistical_demand


class WorkflowLLMStatisticalPlanner(WorkflowLLMPlanner):
    """
    Phase 1 Adapter: Synthesizes execution plan with explicit statistical forecasting step.
    """

    @staticmethod
    def generate_plan(context: OperationalDecisionContext) -> List[WorkflowPlanStep]:
        plan: List[WorkflowPlanStep] = [
            WorkflowPlanStep(
                step_id=1,
                operation_name="audit_effective_inventory",
                description="Sum on-hand and in-transit inventory to compute effective stock position and runway.",
                required_inputs=["on_hand_inventory", "in_transit_inventory", "mean_historical_daily_demand"],
                output_key="inventory_audit"
            ),
            WorkflowPlanStep(
                step_id=2,
                operation_name="evaluate_disturbance_context",
                description="Inspect scenario disturbance metadata to compute safety buffer factor.",
                required_inputs=["scenario_id", "event_name"],
                output_key="disturbance_evaluation"
            ),
            WorkflowPlanStep(
                step_id=3,
                operation_name="statistical_demand_forecast",
                description="Execute Holt-Winters exponential smoothing over lead-time horizon.",
                required_inputs=["mean_historical_daily_demand", "supplier_lead_time_days", "event_name"],
                output_key="statistical_forecast"
            ),
            WorkflowPlanStep(
                step_id=4,
                operation_name="synthesize_target_inventory",
                description="Combine statistical forecast with dynamic safety buffer.",
                required_inputs=["inventory_audit", "disturbance_evaluation", "statistical_forecast"],
                output_key="target_synthesis"
            ),
            WorkflowPlanStep(
                step_id=5,
                operation_name="bind_supplier_constraints",
                description="Calculate net reorder requirement and enforce MOQ and maximum capacity constraints.",
                required_inputs=["inventory_audit", "target_synthesis", "minimum_order_quantity", "maximum_order_quantity"],
                output_key="constrained_order"
            ),
            WorkflowPlanStep(
                step_id=6,
                operation_name="classify_timing_and_risk",
                description="Classify replenishment timing based on stock runway and lead time.",
                required_inputs=["inventory_audit", "constrained_order", "supplier_lead_time_days"],
                output_key="timing_classification"
            )
        ]
        return plan


class WorkflowLLMStatisticalExecutor(WorkflowLLMExecutor):
    """
    Phase 2 Adapter: Executes modified plan including the statistical forecast operation.
    """

    @staticmethod
    def execute_plan(
        plan: List[WorkflowPlanStep],
        context: OperationalDecisionContext
    ) -> Dict[str, Any]:
        execution_state: Dict[str, Any] = {}
        execution_trace: List[Dict[str, Any]] = []

        for step in plan:
            op = step.operation_name

            if op == "audit_effective_inventory":
                on_hand = context.on_hand_inventory
                in_transit = context.in_transit_inventory
                effective = on_hand + in_transit
                daily_d = context.mean_historical_daily_demand
                runway = (effective / daily_d) if daily_d > 0 else 999.0
                out = {
                    "effective_stock": effective,
                    "on_hand": on_hand,
                    "in_transit": in_transit,
                    "runway_days": round(runway, 1)
                }

            elif op == "evaluate_disturbance_context":
                scen = context.scenario_id
                if scen in ("SCEN-02", "SCEN-05"):
                    buffer_factor = 2.0
                elif scen == "SCEN-03":
                    buffer_factor = 1.75
                else:
                    buffer_factor = 1.5

                out = {
                    "buffer_factor": buffer_factor,
                    "scenario_mode": scen
                }

            elif op == "statistical_demand_forecast":
                daily_d = context.mean_historical_daily_demand
                L = context.supplier_lead_time_days
                stat_res = compute_statistical_demand(
                    mean_daily=daily_d,
                    lead_time_days=L,
                    event_name=context.event_name
                )
                out = {
                    "lead_time_demand": stat_res["projected_lead_time_demand"],
                    "event_multiplier": stat_res["event_multiplier"],
                    "model_metadata": stat_res["model_metadata"]
                }

            elif op == "synthesize_target_inventory":
                dist = execution_state["disturbance_evaluation"]
                stat_fc = execution_state["statistical_forecast"]
                daily_d = context.mean_historical_daily_demand
                L = context.supplier_lead_time_days

                lead_time_demand = stat_fc["lead_time_demand"]
                safety_buffer = round(dist["buffer_factor"] * daily_d * (L ** 0.5))
                target_stock = round(lead_time_demand + safety_buffer)

                out = {
                    "lead_time_demand": lead_time_demand,
                    "safety_buffer": safety_buffer,
                    "target_stock": target_stock
                }

            elif op == "bind_supplier_constraints":
                inv = execution_state["inventory_audit"]
                target = execution_state["target_synthesis"]["target_stock"]
                effective = inv["effective_stock"]
                moq = context.minimum_order_quantity
                max_oq = context.maximum_order_quantity

                deficit = target - effective
                if deficit > 0:
                    raw_qty = int(round(deficit))
                    constrained_qty = max(moq, raw_qty)
                    constrained_qty = min(max_oq, constrained_qty)
                else:
                    constrained_qty = 0

                out = {
                    "deficit": deficit,
                    "constrained_order_quantity": constrained_qty
                }

            elif op == "classify_timing_and_risk":
                inv = execution_state["inventory_audit"]
                order = execution_state["constrained_order"]
                L = context.supplier_lead_time_days
                runway = inv["runway_days"]

                if runway < L:
                    timing = "immediate"
                    risk = "high"
                elif runway < 30 and order["constrained_order_quantity"] > 0:
                    timing = "soon"
                    risk = "medium"
                else:
                    timing = "defer"
                    risk = "low"

                out = {
                    "timing": timing,
                    "stockout_risk": risk
                }
            else:
                out = {}

            execution_state[step.output_key] = out
            execution_trace.append({
                "step_id": step.step_id,
                "operation": op,
                "output": out
            })

        execution_state["_trace"] = execution_trace
        return execution_state
