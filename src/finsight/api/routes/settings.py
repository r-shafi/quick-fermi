"""System settings and configuration management API endpoints."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import yaml

from finsight.api.dependencies import enforce_rate_limit, get_current_user, get_db
from finsight.config import PROJECT_ROOT
from finsight.database.repositories import AuditRepository

router = APIRouter(prefix="/api/v1/settings", tags=["System Settings"])


class SettingsResponse(BaseModel):
    currency: str
    forecast_horizon_default: int
    safety_balance_threshold: float
    model_version: str
    llm_provider: str
    demo_mode: bool
    log_level: str
    last_updated: str


class SettingsUpdateRequest(BaseModel):
    currency: Optional[str] = Field(None, description="Default operational currency (e.g. BDT, USD)")
    forecast_horizon_default: Optional[int] = Field(None, ge=1, le=30, description="Default forecast horizon in days")
    safety_balance_threshold: Optional[float] = Field(None, ge=0.0, description="Minimum buffer balance")
    model_version: Optional[str] = Field(None, description="Active ML model version tag")
    llm_provider: Optional[str] = Field(None, description="LLM provider and model identifier")
    demo_mode: Optional[bool] = Field(None, description="Toggle demo/simulation mode")
    log_level: Optional[str] = Field(None, description="Application log level (INFO, DEBUG, etc.)")


def _load_yaml_configs() -> Dict[str, Any]:
    app_cfg_path = PROJECT_ROOT / "configs" / "app.yaml"
    risk_cfg_path = PROJECT_ROOT / "configs" / "risk_policy.yaml"

    app_data: Dict[str, Any] = {}
    risk_data: Dict[str, Any] = {}

    if app_cfg_path.exists():
        with open(app_cfg_path, "r", encoding="utf-8") as f:
            app_data = yaml.safe_load(f) or {}

    if risk_cfg_path.exists():
        with open(risk_cfg_path, "r", encoding="utf-8") as f:
            risk_data = yaml.safe_load(f) or {}

    return {
        "app_cfg": app_data,
        "risk_cfg": risk_data,
        "currency": app_data.get("regional", {}).get("default_currency", "BDT"),
        "forecast_horizon_default": risk_data.get("risk_policy", {}).get("thresholds", {}).get("default_shortfall_horizon_days", 7),
        "safety_balance_threshold": float(risk_data.get("risk_policy", {}).get("thresholds", {}).get("bdt_minimum_safety_balance", 500.0)),
        "model_version": risk_data.get("risk_policy", {}).get("version", "1.0.0"),
        "llm_provider": app_data.get("agent", {}).get("llm_model", "gemini-2.5-flash"),
        "demo_mode": app_data.get("app", {}).get("environment", "development") != "production",
        "log_level": app_data.get("app", {}).get("log_level", "INFO"),
        "last_updated": datetime.utcnow().isoformat(),
    }


@router.get("", response_model=SettingsResponse)
def get_system_settings(
    user_id: str = Depends(get_current_user),
    _rate: None = Depends(enforce_rate_limit),
):
    """Retrieve operational system settings and active risk policy configuration."""
    cfg = _load_yaml_configs()
    return SettingsResponse(
        currency=cfg["currency"],
        forecast_horizon_default=cfg["forecast_horizon_default"],
        safety_balance_threshold=cfg["safety_balance_threshold"],
        model_version=cfg["model_version"],
        llm_provider=cfg["llm_provider"],
        demo_mode=cfg["demo_mode"],
        log_level=cfg["log_level"],
        last_updated=cfg["last_updated"],
    )


@router.post("", response_model=SettingsResponse)
def update_system_settings(
    update_data: SettingsUpdateRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Update system settings with audit logging (Administrator action)."""
    cfg = _load_yaml_configs()
    app_data = cfg["app_cfg"]
    risk_data = cfg["risk_cfg"]

    changes: Dict[str, Any] = {}

    if update_data.currency is not None:
        if "regional" not in app_data:
            app_data["regional"] = {}
        app_data["regional"]["default_currency"] = update_data.currency
        changes["currency"] = update_data.currency

    if update_data.safety_balance_threshold is not None:
        if "regional" not in app_data:
            app_data["regional"] = {}
        app_data["regional"]["bdt_min_safety_buffer"] = update_data.safety_balance_threshold
        if "risk_policy" in risk_data and "thresholds" in risk_data["risk_policy"]:
            risk_data["risk_policy"]["thresholds"]["bdt_minimum_safety_balance"] = update_data.safety_balance_threshold
        changes["safety_balance_threshold"] = update_data.safety_balance_threshold

    if update_data.forecast_horizon_default is not None:
        if "risk_policy" in risk_data and "thresholds" in risk_data["risk_policy"]:
            risk_data["risk_policy"]["thresholds"]["default_shortfall_horizon_days"] = update_data.forecast_horizon_default
        changes["forecast_horizon_default"] = update_data.forecast_horizon_default

    if update_data.model_version is not None:
        if "risk_policy" in risk_data:
            risk_data["risk_policy"]["version"] = update_data.model_version
        changes["model_version"] = update_data.model_version

    if update_data.log_level is not None:
        if "app" not in app_data:
            app_data["app"] = {}
        app_data["app"]["log_level"] = update_data.log_level
        changes["log_level"] = update_data.log_level

    if update_data.demo_mode is not None:
        if "app" not in app_data:
            app_data["app"] = {}
        app_data["app"]["environment"] = "development" if update_data.demo_mode else "production"
        changes["demo_mode"] = update_data.demo_mode

    if update_data.llm_provider is not None:
        if "agent" not in app_data:
            app_data["agent"] = {}
        app_data["agent"]["llm_model"] = update_data.llm_provider
        changes["llm_provider"] = update_data.llm_provider

    # Write back to YAML configs
    app_cfg_path = PROJECT_ROOT / "configs" / "app.yaml"
    risk_cfg_path = PROJECT_ROOT / "configs" / "risk_policy.yaml"

    try:
        with open(app_cfg_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(app_data, f, sort_keys=False)

        if risk_data:
            with open(risk_cfg_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(risk_data, f, sort_keys=False)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist settings: {e}",
        )

    # Record immutable audit event
    audit_repo = AuditRepository(db)
    audit_repo.log_event(
        actor=user_id,
        account_id="SYSTEM",
        action="UPDATE_SYSTEM_SETTINGS",
        status="SUCCESS",
        policy_version=risk_data.get("risk_policy", {}).get("version", "1.0.0"),
        model_version=risk_data.get("risk_policy", {}).get("version", "1.0.0"),
        details={"modified_settings": changes, "timestamp": datetime.utcnow().isoformat()},
    )

    updated_cfg = _load_yaml_configs()
    return SettingsResponse(
        currency=updated_cfg["currency"],
        forecast_horizon_default=updated_cfg["forecast_horizon_default"],
        safety_balance_threshold=updated_cfg["safety_balance_threshold"],
        model_version=updated_cfg["model_version"],
        llm_provider=updated_cfg["llm_provider"],
        demo_mode=updated_cfg["demo_mode"],
        log_level=updated_cfg["log_level"],
        last_updated=updated_cfg["last_updated"],
    )
