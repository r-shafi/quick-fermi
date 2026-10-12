# FinSight AI — Model Card: Shortfall Risk Predictor

## Model Details

- **Model Name:** FinSight Shortfall Tree Classifier
- **Model Version:** `1.0.0`
- **Model Architecture:** Random Forest Classifier (100 estimators, max depth 6) with validation holdout Isotonic Calibration.
- **Trained By:** FinSight AI Pipeline (`scripts/train_models.py`)
- **Primary Objective:** Predict binary financial shortfall $y^{(7)}_T \in \{0, 1\}$ within a 7-day forward horizon, where shortfall is defined as:
  $$y^{(7)}_T = \mathbb{I}\left(\min_{t \in [T, T+7]} \text{Ending Balance}_t < 500.0\text{ BDT}\right)$$
- **License:** Proprietary / Prototype Internal Evaluation
- **Date:** October 2026

---

## Intended Use & Target Users

- **Intended Use Case:** Proactive early-warning financial intervention for personal banking customers and micro/SME enterprises to prevent overdraft fees, missed bill payments, and cash-flow distress.
- **Out-of-Scope Uses:**
  - Automated credit underwriting or loan approvals.
  - Automated debiting, transferring, or investing of user funds.
  - Automated cancellation of essential legal or recurring obligations.

---

## Training Data & Splitting Methodology

- **Dataset Provenance:** Synthetic multi-account benchmark dataset generated via deterministic simulation (`scripts/generate_synthetic_data.py`).
- **Account Profiles:**
  1. `ACC_001_STABLE`: Predictable monthly salary, fixed rent and utilities, regular groceries.
  2. `ACC_002_IRREGULAR`: Freelancer with variable receipts and high discretionary variability.
  3. `ACC_003_SPIKE`: Regular income with episodic luxury/electronics spending spikes.
  4. `ACC_004_DELAYED`: Predictable salary subject to 10-day payment delays in odd months.
  5. `ACC_005_SME`: Business account managing client invoices, supplier invoices, and monthly payroll.
  6. `ACC_006_COLD_START`: Newly onboarded account with $< 10$ days of transaction history.
  7. `ACC_007_EDGE_CASES`: Contains internal transfers, refunds, reversals, and negative ledger excursions.
- **Temporal Splitting Protocol:**
  - Strict time-ordered partitioning: 60% Train, 20% Validation, 20% Test by unique calendar date.
  - Invariant verified: $\max(t_{\text{train}}) < \min(t_{\text{val}}) < \min(t_{\text{test}})$. Zero sample leakage across temporal boundaries.

---

## Performance & Evaluation Metrics

Evaluated on the held-out test split under asymmetric cost penalties ($C_{FN}=5.0, C_{FP}=1.0$):

| Model Architecture | PR-AUC | ROC-AUC | Brier Score | Decision Threshold ($\tau^*$) | Total Test Cost |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Rule-Based Runway Baseline** | 0.8125 | 0.8412 | 0.1420 | Heuristic (< 7 days) | 12.0 |
| **Logistic Regression Baseline** | 0.9412 | 0.9630 | 0.0521 | 0.1800 | 4.0 |
| **Random Forest (Winner)** | **1.0000** | **1.0000** | **0.0001** | **0.0100** | **0.0** |
| **LightGBM Classifier** | 1.0000 | 1.0000 | 0.0002 | 0.0100 | 0.0 |

*Note: On this synthetic benchmark, Random Forest achieved perfect separation on the test set. Performance on real banking data will naturally exhibit higher variance and irreducible noise.*

---

## Explainability (SHAP Tree Explainer)

- **Methodology:** Local SHAP (SHapley Additive exPlanations) values computed via `TreeExplainer` on top of model logits.
- **Top Observed Risk Drivers (Increasing Shortfall Probability):**
  1. Low available bank balance (`verified_available_balance`)
  2. Proximity of large upcoming recurring bills (`days_to_next_major_bill`)
  3. High 7-day spending acceleration (`spending_acceleration_7_vs_30`)
- **Top Observed Risk Mitigators (Decreasing Shortfall Probability):**
  1. High 7-day and 30-day income receipts (`income_sum_7d`, `income_sum_30d`)
  2. High days of solvency runway (`days_of_solvency`)
  3. Low daily spending volatility (`rolling_spend_volatility_30d`)

---

## Ethical Considerations & Known Limitations

1. **Synthetic Data Disclaimer:** This model was trained and evaluated on simulated synthetic data. It has NOT been validated on real customer bank accounts.
2. **Correlation vs. Causation:** SHAP values represent model feature importance in observational data and must NOT be interpreted as causal intervention guarantees.
3. **Emergency Unpredictability:** Sudden external life emergencies (medical crises, natural disasters) cannot be forecasted from historical bank ledger data alone.
4. **Cold-Start Uncertainty:** Accounts with $< 14$ days of history or $< 10$ transactions are flagged as cold start; the model suppresses high-confidence automated actions for these accounts and defaults to human review or conservative advisories.
