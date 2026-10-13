"""Main entrypoint for FinSight AI FastAPI service."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from finsight.api.errors import (
    generic_exception_handler,
    key_error_handler,
    value_error_handler,
)
from finsight.api.routes import (
    accounts,
    approvals,
    audit,
    competition,
    data_quality,
    drift,
    evaluations,
    forecasts,
    health,
    recommendations,
    risk,
    scenario,
    security_tests,
    settings as settings_route,
    transactions,
)
from finsight.database.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    init_db()
    yield


app = FastAPI(
    title="FinSight AI API",
    description=(
        "Cost-Sensitive, Explainable, Predictive Financial Intervention Agent API. "
        "Anticipates cash-flow shortfalls, evaluates error-asymmetric expected costs, "
        "and enforces strict human approval boundaries."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(KeyError, key_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Register routes
app.include_router(health.router)
app.include_router(transactions.router)
app.include_router(accounts.router)
app.include_router(forecasts.router)
app.include_router(risk.router)
app.include_router(recommendations.router)
app.include_router(approvals.router)
app.include_router(evaluations.router)
app.include_router(scenario.router)
app.include_router(audit.router)
app.include_router(security_tests.router)
app.include_router(drift.router)
app.include_router(data_quality.router)
app.include_router(competition.router)
app.include_router(settings_route.router)



@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to FinSight AI API",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("finsight.main:app", host="0.0.0.0", port=8000, reload=True)
