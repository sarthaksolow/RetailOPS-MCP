"""
Same-Repository Architecture Comparison Module.
Exports decision providers representing literature research patterns:
- RetailOps MCP: experiments.m5_operational.decision_provider.RetailOpsDecisionProvider
- Flowr Coordinator: experiments.same_repo_comparison.flowr_coordinator.coordinator.FlowrCoordinatorDecisionProvider
- WorkflowLLM Generative: experiments.same_repo_comparison.workflowllm_generative.generative_workflow.WorkflowLLMDecisionProvider
- Agentic Replenishment: experiments.same_repo_comparison.agentic_replenishment.direct_agent.AgenticReplenishmentDecisionProvider
"""
from experiments.same_repo_comparison.flowr_coordinator.coordinator import FlowrCoordinatorDecisionProvider
from experiments.same_repo_comparison.workflowllm_generative.generative_workflow import WorkflowLLMDecisionProvider
from experiments.same_repo_comparison.agentic_replenishment.direct_agent import AgenticReplenishmentDecisionProvider

__all__ = [
    "FlowrCoordinatorDecisionProvider",
    "WorkflowLLMDecisionProvider",
    "AgenticReplenishmentDecisionProvider"
]
