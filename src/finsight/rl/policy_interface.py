"""Policy interface and candidate policy implementations for offline comparison."""

from abc import ABC, abstractmethod
from typing import Dict, List
import numpy as np


class PolicyInterface(ABC):
    @abstractmethod
    def select_action(self, context: Dict[str, float]) -> str:
        """Select action string given context feature dictionary."""
        pass


class NoInterventionPolicy(PolicyInterface):
    def select_action(self, context: Dict[str, float]) -> str:
        return "NO_INTERVENTION"


class FixedRulePolicy(PolicyInterface):
    """Alerts if balance < 1000 or runway < 7 days."""

    def select_action(self, context: Dict[str, float]) -> str:
        bal = float(context.get("verified_available_balance", 0.0))
        solvency = float(context.get("days_of_solvency", 999.0))
        if bal < 1000.0 or solvency < 7.0:
            return "ALERT"
        return "NO_INTERVENTION"


class CostSensitiveSupervisedPolicy(PolicyInterface):
    """Production policy selecting intervention based on calibrated probability and expected cost."""

    def __init__(self, threshold: float = 0.1667):
        self.threshold = threshold

    def select_action(self, context: Dict[str, float]) -> str:
        bal = float(context.get("verified_available_balance", 0.0))
        bills_7d = float(context.get("known_recurring_bills_next_7d", 0.0))
        disc_ratio = float(context.get("discretionary_spend_ratio_30d", 0.0))

        # Approximate shortfall risk
        is_high_risk = (bal < 1000.0) or (bills_7d > bal)
        if is_high_risk:
            if bills_7d > 0:
                return "BILL_REVIEW"
            elif disc_ratio > 0.20:
                return "BUDGET_PROPOSAL"
            return "ALERT"
        return "INFORM"
