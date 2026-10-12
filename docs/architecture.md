# FinSight AI — System Architecture Document

## 1. System Overview

FinSight AI is a cost-sensitive, explainable, predictive financial intervention system designed to assist personal and SME banking customers (with native BDT multi-currency support) in anticipating and mitigating short-term cash-flow shortfalls before they occur.

Rather than merely reporting historical expenditures or generating conversational suggestions without accountability, FinSight AI integrates:
1. **Deterministic Data Validation & Reconciliation**: Strict schema checks, cryptographic deduplication, and mathematical balance auditing.
2. **Point-in-Time Feature Engineering**: Pure causal feature snapshots with zero lookahead leakage.
3. **Dual-Track Cash-Flow Forecasting**: Deterministic roll-forward baseline paired with probabilistic Monte Carlo simulation across 1, 3, 7, and 14-day horizons.
4. **Cost-Sensitive Risk Classification**: Machine learning models calibrated on validation data and optimized under an asymmetric error cost matrix ($C_{FN}=5.0, C_{FP}=1.0$).
5. **Local Explainability**: Tree SHAP explainers translating model logits into human-understandable drivers, mitigators, and causal limitation disclaimers.
6. **Deterministic Decision Engine & Policy Guardrails**: Expected-cost minimization overriding LLM recommendations and enforcing strict non-negotiable financial safety rules.
7. **Human Approval Workflow & Sandbox Execution**: Isolated state-machine queue where all high-impact actions require explicit human authorization before sandbox dispatch.

---

## 2. End-to-End Architectural Data Flow

```mermaid
graph TD
    subgraph Data Layer
        CSV[Bank Transaction CSV / Open Banking API] --> INGEST[Ingestion & Schema Validator]
        INGEST --> DEDUP[Deduplication & Idempotency Store]
        DEDUP --> RECON[Balance Reconciliation & Audit]
        RECON --> DB[(SQLite / PostgreSQL DB)]
    end

    subgraph Feature & Forecast Layer
        DB --> FEAT[Point-in-Time Feature Pipeline]
        FEAT --> FORECAST[Cashflow Forecaster (Deterministic & Probabilistic)]
    end

    subgraph Risk & ML Layer
        FEAT --> ML[Shortfall Classifier (Random Forest / LightGBM)]
        ML --> CALIB[Validation Probability Calibrator]
        CALIB --> OPT_TAU[Cost-Sensitive Threshold Optimizer (tau*)]
        ML --> SHAP[SHAP Tree Explainer]
    end

    subgraph Decision & Agentic Core
        FORECAST --> POLICY[Deterministic Policy Engine]
        OPT_TAU --> POLICY
        SHAP --> AGENT[FinSight Agentic State Graph]
        POLICY --> AGENT
        AGENT --> GUARD[Deterministic Safety Guardrails]
    end

    subgraph Execution & Delivery
        GUARD --> APPROV[Human Approval Queue]
        APPROV --> DISPATCH[Sandbox Dispatcher & Audit Logger]
        DISPATCH --> AUDIT[(Append-Only Audit Log)]
        AGENT --> API[FastAPI REST API]
        API --> UI[Streamlit Frontend Dashboard]
    end
```

---

## 3. Core Component Boundaries

### 3.1 Ingestion & Reconciliation (`src/finsight/ingestion/`)
- Validates data formats, timestamps with timezone awareness (`Asia/Dhaka`), required numerical fields, and supported currencies.
- Identifies exact transaction duplicate IDs and computes content hashes for idempotency.
- Validates that:
  $$\text{Opening Balance} + \sum \text{Inflows} - \sum \text{Outflows} = \text{Closing Balance}$$
- Reconciles internal transfers between owned accounts (e.g., checking to savings) to ensure internal money movements are not double-counted as spending or income.

### 3.2 Point-in-Time Feature Pipeline (`src/finsight/features/`)
- Strict snapshot timestamps $T$: only records with $t \le T$ are accessible.
- Computes spending velocity, rolling volatility, essential vs. discretionary ratios, income regularity, days since last income, upcoming recurring obligations, and days of solvency.
- Flags cold-start accounts ($< 10$ transactions or $< 14$ days of history) to prevent overconfident ML inference.

### 3.3 Cash-Flow Forecaster (`src/finsight/forecasting/`)
- **Deterministic Forecast**: Evaluates scheduled recurring bills and daily discretionary run-rates across 1, 3, 7, and 14-day horizons.
- **Probabilistic Forecast**: Simulates 500 stochastic paths using empirical variance to yield $P_{10}$ (conservative lower bound), $P_{50}$ (median expectation), and $P_{90}$ (optimistic upper bound).

### 3.4 Risk Modeling & Cost Sensitivity (`src/finsight/ml_core/`)
- Employs calibrated tree ensembles (Random Forest / LightGBM) to estimate shortfall probability $p$.
- Evaluates actions under an explicit financial error cost matrix:
  - $C_{FN} = 5.0$ (penalty for failing to predict a genuine liquidity shortfall).
  - $C_{FP} = 1.0$ (penalty for issuing an unnecessary warning or proposing unwarranted budget cuts).
- Optimizes decision threshold $\tau^*$ on validation data to minimize total cost:
  $$\tau^* = \arg\min_\tau \sum_{i} \text{Cost}(y_i, \mathbb{I}(p_i \ge \tau))$$

### 3.5 Deterministic Policy Engine & Guardrails (`src/finsight/decision/`)
- Computes expected net financial benefit:
  $$\mathbb{E}[\text{Benefit}(a \mid p)] = \mathbb{E}[\text{Cost}(\text{none} \mid p)] - \mathbb{E}[\text{Cost}(a \mid p)]$$
- **Hard Safety Guardrail 1**: Essential recurring payments (rent, mortgage, electricity, water, gas, healthcare, debt repayment, payroll, taxes) can **NEVER** be paused, delayed, or cancelled.
- **Hard Safety Guardrail 2**: Zero real money movements, credit grants, or live balance adjustments are permitted; all execution occurs strictly in `SANDBOX` or `SIMULATION` mode.
- **Hard Safety Guardrail 3**: Mandatory human approval is required for all high-impact intervention types (`BUDGET_PROPOSAL`, `BILL_REVIEW`, `HUMAN_REVIEW`).

### 3.6 Human Approval Queue & Audit Logger (`src/finsight/execution/`)
- Implements an explicit state machine:
  `PROPOSED -> PENDING_APPROVAL -> APPROVED / REJECTED -> EXECUTED_IN_SANDBOX / FAILED`.
- Generates SHA-256 idempotency keys ensuring no proposal can be executed multiple times.
- Persists all state transitions, user identities, timestamps, policy versions, and outcome payloads in an append-only audit log table.

---

## 4. Security & Tenancy Architecture
- Multi-tenant tenant boundary checks enforced in API middleware and dependency injection (`verify_account_ownership`).
- In-memory token bucket rate limiting (120 requests capacity, 2 req/sec refill) guarding against brute-force querying.
- Indirect prompt injection sanitization stripping control sequences (`IGNORE PREVIOUS INSTRUCTIONS`, `SYSTEM PROMPT`, etc.) from merchant and description fields.
