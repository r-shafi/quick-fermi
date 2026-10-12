FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN pip install --upgrade pip && \
    pip install .[dev]

COPY src/ ./src/
COPY configs/ ./configs/
COPY scripts/ ./scripts/
COPY frontend/ ./frontend/
COPY alembic.ini ./

EXPOSE 8000 8501

CMD ["uvicorn", "finsight.main:app", "--host", "0.0.0.0", "--port", "8000"]
