"""Off-policy evaluation comparing candidate policies on simulated test data."""

from typing import Dict, List
import pandas as pd
from finsight.rl.environment import FinancialSimulationEnvironment
from finsight.rl.policy_interface import (
    CostSensitiveSupervisedPolicy,
    FixedRulePolicy,
    NoInterventionPolicy,
    PolicyInterface,
)
from finsight.rl.reward_model import FinancialRewardModel


def evaluate_policy_offline(
    policy: PolicyInterface,
    dataset: pd.DataFrame,
    reward_model: FinancialRewardModel,
) -> Dict[str, any]:
    """Evaluate candidate policy on simulation environment."""
    env = FinancialSimulationEnvironment(dataset=dataset, reward_model=reward_model)
    context = env.reset()
    done = False

    total_reward = 0.0
    action_counts: Dict[str, int] = {}
    shortfalls_prevented = 0
    total_shortfalls = 0

    while not done:
        action = policy.select_action(context)
        action_counts[action] = action_counts.get(action, 0) + 1

        context, reward, done, info = env.step(action)
        total_reward += reward

        if info["actual_target"] == 1:
            total_shortfalls += 1
            if info["shortfall_prevented"]:
                shortfalls_prevented += 1

    n_steps = len(dataset)
    mean_reward = total_reward / max(1, n_steps)
    prevention_rate = shortfalls_prevented / max(1, total_shortfalls)

    return {
        "total_reward": round(total_reward, 2),
        "mean_reward": round(mean_reward, 4),
        "shortfalls_prevented": shortfalls_prevented,
        "total_shortfalls": total_shortfalls,
        "prevention_rate": round(prevention_rate, 4),
        "action_distribution": action_counts,
    }


def compare_all_policies(dataset: pd.DataFrame) -> Dict[str, Dict[str, any]]:
    """Compare all candidate policies on given dataset."""
    reward_model = FinancialRewardModel()
    policies = {
        "no_intervention": NoInterventionPolicy(),
        "fixed_rule_based": FixedRulePolicy(),
        "cost_sensitive_supervised": CostSensitiveSupervisedPolicy(),
    }

    results = {}
    for name, pol in policies.items():
        results[name] = evaluate_policy_offline(pol, dataset, reward_model)

    return results
