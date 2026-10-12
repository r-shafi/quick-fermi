"""Health and system status endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from finsight.config import settings
from finsight.database.session import get_db
from finsight.ml_core.predict import RiskPredictor

router = APIRouter(tags=["Health"])


@router.get("/health")
def get_health(db: Session = Depends(get_db)):
    # Check database connectivity
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    # Check model registry
    predictor = RiskPredictor()
    model_loaded = predictor.package is not None
    model_name = predictor.package.metadata.model_name if model_loaded else "heuristic-baseline"

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "FinSight AI API",
        "version": settings.app.version if hasattr(settings, "app") else "0.1.0",
        "environment": settings.environment,
        "database_connected": db_ok,
        "model_loaded": model_loaded,
        "active_model": model_name,
        "default_currency": settings.regional.default_currency,
        "supported_currencies": settings.regional.supported_currencies,
    }
