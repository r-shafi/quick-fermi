"""Unit tests for cost-sensitive loss, asymmetric cost matrix, and analytical threshold selection."""

import numpy as np
import pytest

from finsight.ml_core.cost_sensitive_loss import CostMatrix
from finsight.ml_core.threshold_selection import select_optimal_threshold
from finsight.decision.expected_cost import (
    InterventionCostParameters,
    compute_expected_cost_for_action,
    compute_expected_cost_inaction,
    evaluate_action,
)


def test_cost_matrix_empirical_calculation():
    # Asymmetric penalties: C_FN = 5.0, C_FP = 1.0, C_TP = 0.0, C_TN = 0.0
    cm = CostMatrix(c_fn=5.0, c_fp=1.0, c_tp=0.0, c_tn=0.0)

    y_true = np.array([1, 1, 0, 0, 1])
    y_pred = np.array([1, 0, 1, 0, 0])
    # TP: idx 0 (1, 1) -> 1
    # TN: idx 3 (0, 0) -> 1
    # FP: idx 2 (0, 1) -> 1
    # FN: idx 1, 4 (1, 0) -> 2

    cost, conf = cm.calculate_empirical_cost(y_true, y_pred)
    assert conf["TP"] == 1
    assert conf["TN"] == 1
    assert conf["FP"] == 1
    assert conf["FN"] == 2

    # Expected: 5.0 * 2 (FN) + 1.0 * 1 (FP) = 11.0
    assert cost == 11.0


def test_analytical_bayes_optimal_threshold():
    # When C_FP = 1.0, C_FN = 5.0, C_TP = 0, C_TN = 0
    # Bayes optimal threshold tau* = C_FP / (C_FP + C_FN) = 1 / (1 + 5) = 1/6 ~= 0.16667
    cm = CostMatrix(c_fn=5.0, c_fp=1.0, c_tp=0.0, c_tn=0.0)
    assert cm.optimal_decision_threshold == pytest.approx(1.0 / 6.0, abs=1e-5)


def test_expected_cost_monotonicity_under_probability():
    cm = CostMatrix(c_fn=5.0, c_fp=1.0, c_tp=0.0, c_tn=0.0)

    # When p = 0: no shortfall possible
    assert cm.compute_expected_cost(0.0, action_alert=True) == 1.0   # FP penalty
    assert cm.compute_expected_cost(0.0, action_alert=False) == 0.0  # Perfect inaction

    # When p = 1: shortfall guaranteed
    assert cm.compute_expected_cost(1.0, action_alert=True) == 0.0   # True alert
    assert cm.compute_expected_cost(1.0, action_alert=False) == 5.0  # Missed shortfall penalty (C_FN)

    # Cross-over point must be tau* = 1/6
    cost_alert_at_cross = cm.compute_expected_cost(1.0 / 6.0, action_alert=True)
    cost_inaction_at_cross = cm.compute_expected_cost(1.0 / 6.0, action_alert=False)
    assert cost_alert_at_cross == pytest.approx(cost_inaction_at_cross, abs=1e-5)


def test_intervention_action_expected_cost_formula():
    params = InterventionCostParameters(
        action_type="ALERT",
        intervention_cost=0.05,
        risk_reduction_factor=0.3,  # alpha = 0.3
        unnecessary_cost=0.2,       # C_unnecessary = 0.2
        mandatory_human_approval=False,
        reversible=True,
    )

    # p = 0.8, c_fn = 5.0
    # E[Cost(a|p)] = (1 - p)*C_unnecessary + p*(1 - alpha)*C_FN + C_a
    # = (0.2)*0.2 + 0.8*(1 - 0.3)*5.0 + 0.05
    # = 0.04 + 0.8*0.7*5.0 + 0.05 = 0.04 + 2.80 + 0.05 = 2.89
    cost_with = compute_expected_cost_for_action(0.8, params, c_fn=5.0)
    assert cost_with == pytest.approx(2.89, abs=1e-4)

    # Inaction: E[Cost(none|p)] = p * C_FN = 0.8 * 5.0 = 4.0
    cost_without = compute_expected_cost_inaction(0.8, c_fn=5.0)
    assert cost_without == pytest.approx(4.0, abs=1e-4)

    # Action evaluation check
    eval_result = evaluate_action(0.8, params, c_fn=5.0)
    assert eval_result.is_cost_effective is True
    assert eval_result.net_cost_benefit == pytest.approx(4.0 - 2.89, abs=1e-4)


def test_select_optimal_threshold_on_validation_predictions():
    cm = CostMatrix(c_fn=5.0, c_fp=1.0)
    y_true = np.array([0, 0, 0, 1, 1, 1, 0, 1])
    y_prob = np.array([0.05, 0.10, 0.15, 0.20, 0.45, 0.85, 0.12, 0.60])

    best_tau, min_cost, curve = select_optimal_threshold(y_prob, y_true, cm)
    assert 0.0 < best_tau < 1.0
    assert min_cost <= cm.calculate_empirical_cost(
        y_true, (y_prob >= 0.5).astype(int)
    )[0]
    assert len(curve) > 0

