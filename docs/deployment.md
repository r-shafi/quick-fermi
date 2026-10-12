# FinSight AI — Deployment & Operations Guide

## 1. Local Environment Setup

### 1.1 Prerequisites
- Linux / macOS / WSL2 environment
- Python 3.12 (or 3.11+)
- Make, Docker, and Docker Compose (optional for containerized deployment)

### 1.2 Installation
```bash
# Clone repository
git clone https://github.com/finsight-ai/finsight-ai.git
cd finsight-ai

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies in editable mode
pip install -e .
```

---

## 2. Running Data Generation, Training & Benchmarks

```bash
# 1. Generate synthetic dataset (7 distinct account profiles + ground truth)
python scripts/generate_synthetic_data.py --seed 42

# 2. Audit and validate dataset reconciliation
python scripts/validate_dataset.py

# 3. Train all 4 model variants (Random Forest, LightGBM, Logistic Regression, Rule Baseline)
python scripts/train_models.py

# 4. Run latency benchmark suite
python scripts/benchmark_latency.py

# 5. Run single-command end-to-end demo walkthrough
python scripts/run_demo.py --account ACC_003_SPIKE
```

---

## 3. Running Services Locally

### 3.1 Start FastAPI Backend Server
```bash
uvicorn finsight.main:app --host 0.0.0.0 --port 8000 --reload
```
- OpenAPI Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### 3.2 Start Streamlit Frontend Dashboard
In a separate terminal:
```bash
source .venv/bin/activate
streamlit run frontend/app.py --server.port 8501
```
- Web Interface: `http://localhost:8501`

---

## 4. Docker & Containerized Deployment

### 4.1 Build and Run with Docker Compose
```bash
docker compose up --build
```
This launches:
- `backend`: FastAPI service on port 8000 with volume mounts for `artifacts/` and `finsight.db`.
- `frontend`: Streamlit service on port 8501 with API routing pointing to `http://backend:8000`.

### 4.2 Verify Service Health
```bash
curl http://localhost:8000/health
```
Response:
```json
{
  "status": "healthy",
  "database": "connected",
  "model_loaded": true,
  "model_name": "random_forest",
  "model_version": "1.0.0"
}
```

---

## 5. Running Automated Tests

```bash
# Run all 65 unit, integration, security, and evaluation tests
pytest tests/ -v

# Run with test coverage report
pytest tests/ --cov=finsight --cov-report=term-missing
```
All 65 tests must pass cleanly.
