"""
Flowr Coordinator Statistical Replacement Provider.
Demonstrates replacement effort under the Centralized Reasoning Coordinator pattern.
Requires creating an adapted tool subclass and coordinator binding adapter.
"""
from experiments.same_repo_comparison.flowr_coordinator.coordinator import FlowrCoordinatorDecisionProvider
from experiments.replacement_modularity_comparison.replacements.flowr.adapted_tools import FlowrStatisticalDomainTools


class FlowrStatisticalReplacementProvider(FlowrCoordinatorDecisionProvider):
    """
    Adapted Flowr coordinator binding the replacement statistical domain tools.
    Surrounding coordinator workflow is preserved via object-oriented subclassing.
    """

    def __init__(self):
        super().__init__()
        self.tools = FlowrStatisticalDomainTools()

    @property
    def provider_id(self) -> str:
        return "flowr_statistical_replacement"
