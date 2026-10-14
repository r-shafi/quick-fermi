.PHONY: install data train evaluate benchmark test run-api run-ui demo clean

VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PYTEST = $(VENV)/bin/pytest
UVICORN = $(VENV)/bin/uvicorn
STREAMLIT = $(VENV)/bin/streamlit

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .[dev]

data:
	$(PYTHON) scripts/generate_synthetic_data.py --seed 42
	$(PYTHON) scripts/validate_dataset.py
	$(PYTHON) scripts/seed_database.py

train:
	$(PYTHON) scripts/train_models.py

evaluate:
	$(PYTHON) scripts/evaluate_models.py

benchmark:
	$(PYTHON) scripts/benchmark_latency.py

test:
	$(PYTEST) tests/ -v --cov=finsight --cov-report=term-missing

run-api:
	$(UVICORN) finsight.main:app --host 0.0.0.0 --port 8000 --reload

run-ui:
	$(STREAMLIT) run frontend/app.py --server.port 8501

demo:
	$(PYTHON) scripts/run_demo.py

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov finsight.db
	find . -type d -name __pycache__ -exec rm -rf {} +
