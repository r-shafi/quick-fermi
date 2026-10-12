"""Simulated contextual bandit environment for financial policy research."""

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from finsight.rl.reward_model import FinancialRewardModel


class FinancialSimulationEnvironment:
    """Contextual environment providing states, actions, and simulated counterfactual rewards."""

    def __init__(self, dataset: pd.DataFrame, reward_model: FinancialRewardModel):
        self.dataset = dataset.copy().reset_index(drop=True)
        self.reward_model = reward_model
        self.current_idx = 0

    def reset(self) -> Dict[str, float]:
        self.current_idx = 0
        return self._get_context(self.current_idx)

    def _get_context(self, idx: int) -> Dict[str, float]:
        row = self.dataset.iloc[idx]
        return row.to_dict()

    def step(self, action: str) -> Tuple[Dict[str, float], float, bool, Dict]:
        """Execute action, return (next_context, reward, done, info)."""
        row = self.dataset.iloc[self.current_idx]
        actual_target = int(row.get("target", 0))

        # Counterfactual simulation of whether action averted shortfall
        action_efficacy = {
            "NO_INTERVENTION": 0.0,
            "INFORM": 0.10,
            "ALERT": 0.40,
            "BUDGET_PROPOSAL": 0.60,
            "BILL_REVIEW": 0.75,
            "HUMAN_REVIEW": 0.90,
        }
        eff = action_efficacy.get(action, 0.0)
        rng = np.random.default_rng(self.current_idx)
        prevented = (actual_target == 1) and (rng.random() < eff)

        reward = self.reward_model.compute_reward(
            action=action,
            actual_shortfall_without_action=actual_target,
            shortfall_prevented=prevented,
        )

        info = {
            "account_id": row.get("account_id"),
            "snapshot_date": row.get("snapshot_date"),
            "actual_target": actual_target,
            "shortfall_prevented": prevented,
            "action": action,
        }

        self.current_idx += 1
        done = self.current_idx >= len(self.dataset)
        next_context = self._get_context(self.current_idx) if not done else {}

        return next_context, reward, done, info
