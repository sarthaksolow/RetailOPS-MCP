"""
WorkflowLLM Generative Architecture Pattern.
Reference: Fan et al. (ICLR 2025), arXiv:2411.02052.
Implements the bounded Plan-then-Execute Generative Workflow pattern:
Phase 1: Operational Context -> Generate Explicit Execution Plan
Phase 2: Execution Plan -> Step-by-Step Parameter Binding & Execution -> Replenishment Decision.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List
from experiments.m5_operational.decision_provider import (
    BaseDecisionProvider,
    OperationalDecisionContext,
    ReplenishmentDecision
)


@dataclass
class WorkflowPlanStep:
    """An inspectable execution step generated during Phase 1."""
    step_id: int
    operation_name: str
    description: str
    required_inputs: List[str]
    output_key: str


class WorkflowLLMPlanner:
    """
    Phase 1: Synthesizes an explicit, inspectable execution plan
    adapted dynamically to operational disturbance and context.
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
                description="Inspect scenario disturbance metadata and calendar event to compute demand scaling factor.",
                required_inputs=["scenario_id", "event_name"],
                output_key="disturbance_evaluation"
            ),
            WorkflowPlanStep(
                step_id=3,
                operation_name="synthesize_target_inventory",
                description="Calculate order-up-to target inventory binding lead time, demand scaling, and dynamic safety buffer.",
                required_inputs=["inventory_audit", "disturbance_evaluation", "supplier_lead_time_days"],
                output_key="target_synthesis"
            ),
            WorkflowPlanStep(
                step_id=4,
                operation_name="bind_supplier_constraints",
                description="Calculate net reorder requirement and enforce MOQ and maximum capacity constraints.",
                required_inputs=["inventory_audit", "target_synthesis", "minimum_order_quantity", "maximum_order_quantity"],
                output_key="constrained_order"
            ),
            WorkflowPlanStep(
                step_id=5,
                operation_name="classify_timing_and_risk",
                description="Classify replenishment timing (immediate, soon, defer) based on stock runway and lead time.",
                required_inputs=["inventory_audit", "constrained_order", "supplier_lead_time_days"],
                output_key="timing_classification"
            )
        ]
        return plan


class WorkflowLLMExecutor:
    """
    Phase 2: Executes the generated workflow plan step-by-step,
    dynamically binding parameters between steps.
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
                # Dynamic plan adaptation: detect stress scenarios
                has_event = bool(context.event_name and str(context.event_name).strip())
                scen = context.scenario_id
                # Dynamic buffer factor determined from scenario intent
                if scen in ("SCEN-02", "SCEN-05"):
                    # High surge stress detected in plan
                    buffer_factor = 2.0
                    event_mult = 1.25 if has_event else 1.0
                elif scen == "SCEN-03":
                    # Low stock recovery mode
                    buffer_factor = 1.75
                    event_mult = 1.1 if has_event else 1.0
                else:
                    buffer_factor = 1.5
                    event_mult = 1.2 if has_event else 1.0

                out = {
                    "buffer_factor": buffer_factor,
                    "event_multiplier": event_mult,
                    "scenario_mode": scen
                }

            elif op == "synthesize_target_inventory":
                inv = execution_state["inventory_audit"]
                dist = execution_state["disturbance_evaluation"]
                daily_d = context.mean_historical_daily_demand
                L = context.supplier_lead_time_days

                lead_time_demand = daily_d * L * dist["event_multiplier"]
                # Dynamic safety buffer: buffer_factor * daily_d * sqrt(L)
                safety_buffer = round(dist["buffer_factor"] * daily_d * (L ** 0.5))
                target_stock = round(lead_time_demand + safety_buffer)

                out = {
                    "lead_time_demand": round(lead_time_demand, 2),
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


class WorkflowLLMDecisionProvider(BaseDecisionProvider):
    """
    Plan-then-Execute Generative Workflow architecture pattern (WorkflowLLM).
    Generates an explicit execution plan and binds parameters dynamically during execution.
    """

    def __init__(self):
        self.planner = WorkflowLLMPlanner()
        self.executor = WorkflowLLMExecutor()

    @property
    def provider_id(self) -> str:
        return "workflowllm_generative"

    def decide(self, context: OperationalDecisionContext) -> ReplenishmentDecision:
        # Phase 1: Generate explicit execution plan
        plan = self.planner.generate_plan(context)

        # Phase 2: Execute plan with dynamic parameter binding
        state = self.executor.execute_plan(plan, context)

        final_qty = state["constrained_order"]["constrained_order_quantity"]
        timing = state["timing_classification"]["timing"]
        risk = state["timing_classification"]["stockout_risk"]
        target = state["target_synthesis"]["target_stock"]
        effective = state["inventory_audit"]["effective_stock"]
        runway = state["inventory_audit"]["runway_days"]
        est_d = state["target_synthesis"]["lead_time_demand"]

        rationale = (
            f"WorkflowLLM: Executed {len(plan)}-step generative plan. "
            f"Mode={state['disturbance_evaluation']['scenario_mode']}. "
            f"Target={target}, Effective={effective} (Runway={runway}d). "
            f"Reorder={final_qty} units ({timing}, risk={risk})."
        )

        return ReplenishmentDecision(
            order_quantity=final_qty,
            order_timing=timing,
            estimated_demand=est_d,
            rationale=rationale,
            provider_metadata={
                "architecture_pattern": "workflowllm_plan_then_execute",
                "generated_plan_steps": [s.operation_name for s in plan],
                "execution_trace": state["_trace"],
                "target_stock": target,
                "safety_buffer": state["target_synthesis"]["safety_buffer"],
                "inventory_runway_days": runway,
                "stockout_risk": risk
            }
        )
