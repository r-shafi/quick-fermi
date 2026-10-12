"""Temporal features extracted at snapshot timestamp."""

from datetime import datetime
from typing import Dict


def extract_temporal_features(snapshot_dt: datetime) -> Dict[str, float]:
    """Extract calendar and cyclical temporal features from snapshot timestamp."""
    return {
        "day_of_week": float(snapshot_dt.weekday()),  # 0 = Monday, 6 = Sunday
        "day_of_month": float(snapshot_dt.day),
        "is_weekend": 1.0 if snapshot_dt.weekday() >= 5 else 0.0,
        "is_month_start": 1.0 if snapshot_dt.day <= 5 else 0.0,
        "is_month_end": 1.0 if snapshot_dt.day >= 25 else 0.0,
    }
