"""
WorkflowLLM Generative Statistical Replacement Provider.
Demonstrates replacement effort under the Plan-then-Execute Generative Workflow pattern.
Requires modifying both Phase 1 plan schema and Phase 2 executor dispatch.
"""
from experiments.m5_operational.decision_provider import (
    BaseDecisionProvider,
    OperationalDecisionContext,
    ReplenishmentDecision
)
from experiments.replacement_modularity_comparison.replacements.workflowllm.adapted_workflow import (
    WorkflowLLMStatisticalPlanner,
    WorkflowLLMStatisticalExecutor
)


class WorkflowLLMStatisticalReplacementProvider(BaseDecisionProvider):
    """
    Adapted WorkflowLLM decision provider executing the updated statistical plan.
    """

    def __init__(self):
        self.planner = WorkflowLLMStatisticalPlanner()
        self.executor = WorkflowLLMStatisticalExecutor()

    @property
    def provider_id(self) -> str:
        return "workflowllm_statistical_replacement"

    def decide(self, context: OperationalDecisionContext) -> ReplenishmentDecision:
        # Phase 1: Generate updated 6-step execution plan with statistical forecast
        plan = self.planner.generate_plan(context)

        # Phase 2: Execute plan with statistical step binding
        state = self.executor.execute_plan(plan, context)

        final_qty = state["constrained_order"]["constrained_order_quantity"]
        timing = state["timing_classification"]["timing"]
        risk = state["timing_classification"]["stockout_risk"]
        target = state["target_synthesis"]["target_stock"]
        effective = state["inventory_audit"]["effective_stock"]
        runway = state["inventory_audit"]["runway_days"]
        est_d = state["target_synthesis"]["lead_time_demand"]

        rationale = (
            f"WorkflowLLM Statistical Replacement: Executed {len(plan)}-step generative plan. "
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
                "architecture_pattern": "workflowllm_statistical_replacement",
                "generated_plan_steps": [s.operation_name for s in plan],
                "execution_trace": state["_trace"],
                "target_stock": target,
                "safety_buffer": state["target_synthesis"]["safety_buffer"],
                "inventory_runway_days": runway,
                "stockout_risk": risk
            }
        )
