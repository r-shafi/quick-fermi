# FinSight AI — Evaluation Protocol & Metric Definitions

## 1. Principles of Financial ML Evaluation

Standard machine learning models in consumer finance are typically trained and evaluated using symmetric loss functions (Log-Loss, Cross-Entropy) and evaluated using threshold-agnostic rankings (ROC-AUC). In operational financial interventions, however:
1. **Errors are Highly Asymmetric:** A False Negative (failing to alert a user about an impending liquidity crisis) causes overdraft penalties, bounced bills, and reputational distress. A False Positive (a precautionary advisory when no shortfall happens) causes minor annoyance or brief fatigue.
2. **Causality & Time-Ordering are Non-Negotiable:** K-Fold cross validation randomly shuffles future transactions into training folds, causing fatal data leakage. All evaluation must be strictly time-ordered.
3. **Probability Calibration is Critical:** Raw model outputs cannot be plugged into expected-cost equations without empirical calibration.

---

## 2. Temporal Splitting Protocol

Given historical transaction records spanning $[T_0, T_{max}]$:
1. **Train Fold ($60\%$ of calendar dates):** $T \in [T_0, T_{train}]$
2. **Validation Fold ($20\%$ of calendar dates):** $T \in (T_{train}, T_{val}]$
   - Used *exclusively* for:
     - Fitting the probability calibrator (`ModelCalibrator`)
     - Optimizing the cost-sensitive decision threshold $\tau^*$
3. **Test Fold ($20\%$ of calendar dates):** $T \in (T_{val}, T_{max}]$
   - Held out completely until final scoring.
   - Evaluated using frozen calibrator and frozen threshold $\tau^*$.

---

## 3. Mathematical Metric Definitions

### 3.1 Asymmetric Financial Error Cost
Given empirical confusion matrix $\{TP, TN, FP, FN\}$:
$$\text{Total Cost} = C_{FN} \cdot FN + C_{FP} \cdot FP + C_{TP} \cdot TP + C_{TN} \cdot TN$$
Where default system parameters are:
- $C_{FN} = 5.0$
- $C_{FP} = 1.0$
- $C_{TP} = 0.0$
- $C_{TN} = 0.0$

### 3.2 Expected Cost Formula for Continuous Probability $p$
For an individual account with calibrated shortfall probability $p$:
- **Expected Cost of Inaction (No Warning):**
  $$\mathbb{E}[\text{Cost}(\text{none} \mid p)] = p \cdot C_{FN}$$
- **Expected Cost of Proposed Action $a$:**
  $$\mathbb{E}[\text{Cost}(a \mid p)] = (1 - p) \cdot C_{\text{unnecessary}, a} + p \cdot (1 - \alpha_a) \cdot C_{FN} + C_a$$
  Where:
  - $\alpha_a \in [0, 1]$ is the empirical risk reduction factor.
  - $C_a$ is the direct cost of applying the intervention.
  - $C_{\text{unnecessary}, a}$ is the penalty incurred if the shortfall does not occur.

### 3.3 Probability Calibration (Brier Score & ECE)
- **Brier Score:**
  $$\text{Brier} = \frac{1}{N} \sum_{i=1}^N (p_i - y_i)^2$$
- **Expected Calibration Error (ECE):**
  $$\text{ECE} = \sum_{m=1}^M \frac{|B_m|}{N} \left| \text{acc}(B_m) - \text{conf}(B_m) \right|$$

### 3.4 Cash-Flow Forecast Accuracy & Coverage
- **Point Accuracy:** Mean Absolute Error ($\text{MAE}$) and Root Mean Squared Error ($\text{RMSE}$) on projected balance trajectories.
- **Interval Coverage:** Empirical percentage of actual future balances falling within the $[P_{10}, P_{90}]$ prediction interval (nominal target: $80\%$).
- **Interval Width:** $\text{Mean}(P_{90} - P_{10})$; narrow intervals with high coverage represent superior probabilistic uncertainty estimates.
