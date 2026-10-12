"""Model registry for versioning, artifact serialization, and schema validation."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import pandas as pd
from pydantic import BaseModel, Field

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "artifacts" / "models"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


class ModelMetadata(BaseModel):
    model_version: str
    model_name: str
    target_name: str
    target_version: str = "1.0.0"
    training_data_fingerprint: str
    training_cutoff_date: str
    feature_schema: List[str]
    decision_threshold: float
    calibration_method: str
    validation_metrics: Dict[str, Any] = Field(default_factory=dict)
    library_versions: Dict[str, str] = Field(default_factory=dict)


class RegisteredModelPackage:
    """Encapsulates trained model, calibrator, explainer, and strict schema validation."""

    def __init__(
        self,
        model: Any,
        calibrator: Any,
        metadata: ModelMetadata,
        explainer: Optional[Any] = None,
    ):
        self.model = model
        self.calibrator = calibrator
        self.metadata = metadata
        self.explainer = explainer

    def validate_features(self, X: pd.DataFrame):
        """Validate input feature schema against registered schema."""
        missing = [col for col in self.metadata.feature_schema if col not in X.columns]
        if missing:
            raise ValueError(
                f"Incompatible feature schema for model '{self.metadata.model_name}' "
                f"v{self.metadata.model_version}. Missing required features: {missing}"
            )

    def predict_proba(self, X: pd.DataFrame) -> float:
        """Predict calibrated probability for a single instance or batch."""
        self.validate_features(X)
        X_ordered = X[self.metadata.feature_schema]

        if hasattr(self.model, "predict_proba"):
            raw_p = self.model.predict_proba(X_ordered)[:, 1]
        else:
            raw_p = self.model.predict(X_ordered)

        if self.calibrator is not None and hasattr(self.calibrator, "predict_proba"):
            cal_p = self.calibrator.predict_proba(raw_p)
        else:
            cal_p = raw_p

        return float(cal_p[0]) if len(cal_p) == 1 else cal_p

    def save(self, directory: Optional[Path] = None) -> Path:
        """Save registered model package and metadata to disk."""
        save_dir = directory or (ARTIFACTS_DIR / f"{self.metadata.model_name}_{self.metadata.model_version}")
        save_dir.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.model, save_dir / "model.joblib")
        joblib.dump(self.calibrator, save_dir / "calibrator.joblib")
        if self.explainer is not None:
            joblib.dump(self.explainer, save_dir / "explainer.joblib")

        with open(save_dir / "metadata.json", "w", encoding="utf-8") as f:
            f.write(self.metadata.model_dump_json(indent=2))

        return save_dir

    @classmethod
    def load(cls, save_dir: Path) -> "RegisteredModelPackage":
        """Load registered model package from directory."""
        with open(save_dir / "metadata.json", "r", encoding="utf-8") as f:
            meta_dict = json.load(f)
        metadata = ModelMetadata(**meta_dict)

        model = joblib.load(save_dir / "model.joblib")
        calibrator = joblib.load(save_dir / "calibrator.joblib") if (save_dir / "calibrator.joblib").exists() else None
        explainer = joblib.load(save_dir / "explainer.joblib") if (save_dir / "explainer.joblib").exists() else None

        return cls(model=model, calibrator=calibrator, metadata=metadata, explainer=explainer)
