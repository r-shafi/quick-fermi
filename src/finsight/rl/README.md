# FinSight AI — Reinforcement Learning Research Module

> [!WARNING]
> **RESEARCH MODULE ONLY — NOT DEPLOYED IN PRODUCTION DECISION PATH**
> This module is strictly isolated from production financial interventions. The live system relies exclusively on the supervised risk model and deterministic expected-cost policy engine with non-negotiable safety guardrails.

## Objectives and Scope
This package provides a simulation-based research testbed for evaluating **Contextual Bandits** and **Offline Policy Optimization** under multi-objective financial reward formulations:

1. **Context Space**: Financial feature vectors extracted at snapshot time $T$ (liquidity runway, spending acceleration, upcoming obligations, rolling volatility).
2. **Action Space**: Safe discrete interventions matching the approved catalog:
   - $a_0$: `NO_INTERVENTION`
   - $a_1$: `INFORM`
   - $a_2$: `ALERT`
   - $a_3$: `BUDGET_PROPOSAL`
   - $a_4$: `BILL_REVIEW`
   - $a_5$: `HUMAN_REVIEW`
3. **Reward Formulation**:
   $$\text{Reward}(s, a, y) = \text{AvoidedShortfallBenefit}(y, a) - \text{DirectInterventionCost}(a) - \text{UserFatigueCost}(a)$$
4. **Safety Guarantee**: Even within the research environment, actions that attempt to cancel essential bills or move money are rejected by `validate_action_constraints`.

## Offline Evaluation (OPE)
The offline evaluation compares four policies on logged synthetic simulation data:
1. **Never Intervene** ($a_0$)
2. **Fixed Rule-Based Policy** (Alert when balance < threshold)
3. **Supervised Expected-Cost Policy** (Production baseline)
4. **Contextual Bandit Policy** (Trained on historical logged propensities via Inverse Propensity Scoring)

## Limitations and Disclaimers
- Simulated policy reward gains **do not guarantee real customer financial benefit**.
- Online epsilon-greedy exploration on real customer accounts is **unconditionally forbidden**.
