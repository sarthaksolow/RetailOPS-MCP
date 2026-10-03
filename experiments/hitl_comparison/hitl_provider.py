"""
Human-in-the-Loop (HITL) Decision Providers for M5 Operational Comparison.
Evaluates:
1. Mode A: Fully Autonomous Operation (retailops_autonomous)
2. Mode B: Human-Supervised Operation with Approval Gate (retailops_human_supervised)

Note on Scientific Modeling:
The human operator is modeled explicitly as a deterministic, reproducible simulated operator
policy adhering strictly to the governance criteria defined in PROTOCOL-EXP-FROZEN-V1 Section 5.2.
This avoids non-reproducible external human variance while accurately evaluating the
structural effects of interception, escalation, override, and latency.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from experiments.m5_operational.decision_provider import (
    BaseDecisionProvider,
    OperationalDecisionContext,
    ReplenishmentDecision,
    RetailOpsDecisionProvider
)


class RetailOpsAutonomousProvider(BaseDecisionProvider):
    """
    Mode A: Fully Autonomous Decision Flow.
    Directly commits replenishment decisions produced by RetailOps reasoning logic
    without approval gates or human oversight.
    """

    def __init__(self):
        self._underlying = RetailOpsDecisionProvider()

    @property
    def provider_id(self) -> str:
        return "retailops_autonomous"

    def decide(self, context: OperationalDecisionContext) -> ReplenishmentDecision:
        decision = self._underlying.decide(context)

        # Annotate with autonomous mode governance metadata
        meta = dict(decision.provider_metadata)
        meta.update({
            "hitl_mode": "autonomous",
            "gate_triggered": False,
            "escalated": False,
            "operator_action": "NONE",
            "approval_latency_seconds": 0.0,
            "policy_violation_prevented": False,
            "original_proposed_quantity": decision.order_quantity
        })

        return ReplenishmentDecision(
            order_quantity=decision.order_quantity,
            order_timing=decision.order_timing,
            estimated_demand=decision.estimated_demand,
            rationale=f"[Autonomous Mode] {decision.rationale}",
            provider_metadata=meta
        )


class RetailOpsSupervisedProvider(BaseDecisionProvider):
    """
    Mode B: Human-Supervised Decision Flow.
    Uses the identical RetailOps replenishment reasoning pipeline, but routes proposals
    through an explicit, reproducible approval gate (simulated operator policy).

    Interception Checkpoints (strictly per PROTOCOL-EXP-FROZEN-V1 Section 5.2):
    1. Stockout risk classified as 'high' (runway < lead_time).
    2. Order quantity exceeds 2.5x safety stock buffer.
    3. Order expenditure exceeds single-order budget threshold ($100.00).
    4. Extended lead-time arrival boundary (orders arriving past horizon H=28: current_day + L > 28).

    Simulated Operator Actions:
    - APPROVE: Proposal verified and committed as generated.
    - OVERRIDE: Proposed quantity adjusted or tempered to protect working capital or prevent late arrivals.
    - REJECT: Proposal cancelled.
    """

    def __init__(
        self,
        budget_threshold_usd: float = 100.0,
        simulated_review_latency_seconds: float = 15.0
    ):
        self._underlying = RetailOpsDecisionProvider()
        self.budget_threshold_usd = budget_threshold_usd
        self.simulated_review_latency_seconds = simulated_review_latency_seconds

    @property
    def provider_id(self) -> str:
        return "retailops_human_supervised"

    def decide(self, context: OperationalDecisionContext) -> ReplenishmentDecision:
        # Step 1: Generate proposed replenishment decision via standard RetailOps pipeline
        proposal = self._underlying.decide(context)
        proposed_qty = proposal.order_quantity
        meta = dict(proposal.provider_metadata)

        daily_d = context.mean_historical_daily_demand
        L = context.supplier_lead_time_days
        runway = meta.get("stock_runway_days", 999.0)
        safety_stock = meta.get("safety_stock", round(daily_d * L * 1.25))
        expenditure = proposed_qty * context.unit_cost

        # Step 2: Evaluate Escalation Criteria
        escalate_reasons: List[str] = []

        # Check 1: Stockout risk classified as high
        if proposal.order_timing == "immediate" or runway < L:
            escalate_reasons.append(f"high_stockout_risk (runway {runway:.1f}d < L {L}d)")

        # Check 2: Proposed quantity exceeds 2.5x historical safety stock
        if proposed_qty > (2.5 * safety_stock) and proposed_qty > 0:
            escalate_reasons.append(f"excessive_quantity ({proposed_qty} > 2.5x safety stock {safety_stock})")

        # Check 3: Expenditure exceeds budget threshold
        if expenditure > self.budget_threshold_usd and proposed_qty > 0:
            escalate_reasons.append(f"budget_threshold_exceeded (${expenditure:.2f} > ${self.budget_threshold_usd:.2f})")

        # Check 4: Supplier delay horizon boundary (orders arriving past horizon H=28)
        if (context.current_day + L) > 28 and proposed_qty > 0:
            escalate_reasons.append(f"late_arrival_past_horizon (day {context.current_day} + L {L} = {context.current_day + L} > 28)")

        is_escalated = len(escalate_reasons) > 0

        # Step 3: Simulated Operator Resolution
        final_qty = proposed_qty
        operator_action = "APPROVE"
        policy_violation_prevented = False
        latency = 0.0
        operator_notes = ""

        if not is_escalated:
            # Low risk: Automated pass-through approval
            operator_action = "APPROVE"
            latency = 0.0
            operator_notes = "Normal operational parameters; automated pass-through approval."
        else:
            # Escalated: Operator reviews proposal with simulated deliberation latency
            latency = self.simulated_review_latency_seconds

            # Rule A: Prevent pipeline orders arriving past evaluation horizon (day + L > 28) when runway is safe
            if (context.current_day + L) > 28 and runway >= 3.0:
                final_qty = 0
                operator_action = "OVERRIDE"
                policy_violation_prevented = True
                operator_notes = (
                    f"Operator Override: Cancelled late order of {proposed_qty} units. "
                    f"Order placed on day {context.current_day} with L={L} arrives past simulation horizon (day {context.current_day + L}). "
                    f"Current stock runway {runway:.1f}d is adequate."
                )

            # Rule B: Enforce budget cap ($100) on single-order expenditure
            elif expenditure > self.budget_threshold_usd:
                max_budget_qty = max(context.minimum_order_quantity, int(self.budget_threshold_usd / context.unit_cost))
                max_budget_qty = min(context.maximum_order_quantity, max_budget_qty)
                if max_budget_qty < proposed_qty:
                    final_qty = max_budget_qty
                    operator_action = "OVERRIDE"
                    policy_violation_prevented = True
                    operator_notes = (
                        f"Operator Override: Capped expenditure from {proposed_qty} units (${expenditure:.2f}) "
                        f"to {final_qty} units (${final_qty * context.unit_cost:.2f}) to comply with budget limit."
                    )
                else:
                    operator_action = "APPROVE"
                    operator_notes = f"Operator Approved: Budget compliance verified at MOQ threshold ({final_qty} units)."

            # Rule C: Temper excessive order quantities exceeding 2.5x safety stock
            elif proposed_qty > (2.5 * safety_stock):
                capped_qty = max(context.minimum_order_quantity, int(round(2.0 * safety_stock)))
                capped_qty = min(context.maximum_order_quantity, capped_qty)

                if capped_qty < proposed_qty:
                    final_qty = capped_qty
                    operator_action = "OVERRIDE"
                    policy_violation_prevented = True
                    operator_notes = (
                        f"Operator Override: Tempered surge order from {proposed_qty} to {final_qty} units "
                        f"(capped at 2.0x safety stock {safety_stock}) to prevent inventory glut."
                    )
                else:
                    operator_action = "APPROVE"
                    operator_notes = f"Operator Approved: Large order {proposed_qty} units necessary to prevent stockout under stress."

            # Rule D: Critical stockout emergency (runway < 2 days)
            elif runway < 2.0 and proposed_qty > 0:
                operator_action = "APPROVE"
                operator_notes = f"Operator Approved: Confirmed emergency replenishment of {proposed_qty} units (critical runway {runway:.1f}d)."

            else:
                operator_action = "APPROVE"
                operator_notes = f"Operator Approved: Reviewed proposal of {proposed_qty} units; deemed acceptable."

        # Compile final decision
        meta.update({
            "hitl_mode": "human_supervised",
            "gate_triggered": is_escalated,
            "escalated": is_escalated,
            "escalation_reasons": escalate_reasons,
            "operator_action": operator_action,
            "approval_latency_seconds": latency,
            "policy_violation_prevented": policy_violation_prevented,
            "original_proposed_quantity": proposed_qty,
            "supervised_final_quantity": final_qty,
            "operator_notes": operator_notes
        })

        # Update order timing if overridden to zero
        final_timing = proposal.order_timing
        if final_qty == 0:
            final_timing = "defer"

        rationale = (
            f"[Supervised Mode] Operator Action: {operator_action} "
            f"(Proposed: {proposed_qty}, Final: {final_qty}, Latency: {latency:.1f}s). "
            f"{operator_notes}"
        )

        return ReplenishmentDecision(
            order_quantity=final_qty,
            order_timing=final_timing,
            estimated_demand=proposal.estimated_demand,
            rationale=rationale,
            provider_metadata=meta
        )
