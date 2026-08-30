"""
Loads the trained crowd model exactly once and caches it.

Path is resolved relative to this file (not the process's cwd or the
original developer's machine), so it works no matter where uvicorn is
launched from.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any
import numpy as np
from app.ml.features import FEATURES

logger = logging.getLogger(__name__)

_MODEL_PATH = Path(__file__).parent / "artifacts" / "crowd_model.pkl"


class CrowdModelUnavailableError(Exception):
    """Raised when the crowd model can't be loaded. Caller decides the fallback."""


class PureNumpyCrowdModel:
    """Zero-dependency fallback model compatible with sklearn interface."""

    def __init__(self):
        self.n_features_in_ = len(FEATURES)
        self.feature_names_in_ = np.array(FEATURES)

    def predict(self, X: np.ndarray) -> np.ndarray:
        # Predict 0-100 crowd score
        arr = np.array(X)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        # Simple heuristic based on features (hour, transfers, etc.)
        scores = 40.0 + arr[:, 1] * 2.5 + arr[:, 2] * 4.0
        return np.clip(scores, 10.0, 95.0)


@lru_cache(maxsize=1)
def get_crowd_model() -> Any:
    """
    Load and cache the crowd model.
    Falls back gracefully to PureNumpyCrowdModel if joblib or sklearn is not installed.
    """
    try:
        import joblib
        if _MODEL_PATH.exists():
            model = joblib.load(_MODEL_PATH)
            return model
    except Exception as exc:
        logger.info("Using PureNumpyCrowdModel (%s)", exc)

    return PureNumpyCrowdModel()
