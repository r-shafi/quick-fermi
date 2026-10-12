"""Multi-objective financial reward model for RL/Bandit simulation."""

from typing import Dict
from finsight.decision.intervention_catalog import InterventionType


class FinancialRewardModel:
    """Calculates multi-objective financial reward balancing safety, intervention cost, and user burden."""

    def __init__(
        self,
        shortfall_penalty: float = 5.0,     # Penalty if shortfall occurs
        avoided_shortfall_value: float = 4.0, # Reward if intervention averted a shortfall
        unnecessary_alert_penalty: float = 1.0,
    ):
        self.shortfall_penalty = shortfall_penalty
        self.avoided_shortfall_value = avoided_shortfall_value
        self.unnecessary_alert_penalty = unnecessary_alert_penalty

    def compute_reward(
        self,
        action: str,
        actual_shortfall_without_action: int,
        shortfall_prevented: bool,
    ) -> float:
        """Compute scalar reward for an action given simulated outcome."""
        # Baseline cost if no intervention taken
        if action == "NO_INTERVENTION":
            return -self.shortfall_penalty if actual_shortfall_without_action == 1 else 0.5

        # Direct costs and user burden by action
        action_burdens = {
            "INFORM": 0.05,
            "ALERT": 0.30,
            "BUDGET_PROPOSAL": 0.80,
            "BILL_REVIEW": 1.00,
            "HUMAN_REVIEW": 2.50,
        }
        burden = action_burdens.get(action, 0.5)

        if actual_shortfall_without_action == 1:
            if shortfall_prevented:
                # Successfully mitigated shortfall
                return self.avoided_shortfall_value - burden
            else:
                # Shortfall occurred despite intervention
                return -self.shortfall_penalty - burden
        else:
            # Unnecessary intervention (false positive burden)
            return -self.unnecessary_alert_penalty - burden
