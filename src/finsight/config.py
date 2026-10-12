"""Configuration loading and validation for FinSight AI."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
REPORTS_DIR = ARTIFACTS_DIR / "reports"
MODELS_DIR = ARTIFACTS_DIR / "models"


def load_yaml(filename: str) -> Dict[str, Any]:
    path = CONFIGS_DIR / filename
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class RegionalSettings(BaseModel):
    default_currency: str = "BDT"
    supported_currencies: List[str] = ["BDT", "USD", "EUR", "GBP"]
    bdt_min_safety_buffer: float = 500.0
    usd_min_safety_buffer: float = 50.0
    timezone: str = "Asia/Dhaka"


class SecuritySettings(BaseModel):
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    rate_limit_per_minute: int = 120
    mask_pii: bool = True
    secret_key: str = "dev-secret-key-change-in-production-finsight-928374"


class AppSettings(BaseSettings):
    environment: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    frontend_port: int = 8501
    database_url: str = "sqlite:///./finsight.db"
    regional: RegionalSettings = Field(default_factory=RegionalSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    class Config:
        env_file = ".env"
        extra = "ignore"


class RiskPolicyConfig:
    """Helper to access risk policy configuration."""

    def __init__(self):
        self._data = load_yaml("risk_policy.yaml").get("risk_policy", {})

    @property
    def c_fn(self) -> float:
        return float(self._data.get("error_costs", {}).get("c_fn", 5.0))

    @property
    def c_fp(self) -> float:
        return float(self._data.get("error_costs", {}).get("c_fp", 1.0))

    @property
    def default_horizon_days(self) -> int:
        return int(self._data.get("thresholds", {}).get("default_shortfall_horizon_days", 7))

    @property
    def bdt_safety_buffer(self) -> float:
        return float(self._data.get("thresholds", {}).get("bdt_minimum_safety_balance", 500.0))

    @property
    def raw(self) -> Dict[str, Any]:
        return self._data


# Global singletons
settings = AppSettings()
risk_policy_config = RiskPolicyConfig()
