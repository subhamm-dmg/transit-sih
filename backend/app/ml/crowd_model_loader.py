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

logger = logging.getLogger(__name__)

_MODEL_PATH = Path(__file__).parent / "artifacts" / "crowd_model.pkl"


class CrowdModelUnavailableError(Exception):
    """Raised when the crowd model can't be loaded. Caller decides the fallback."""


@lru_cache(maxsize=1)
def get_crowd_model() -> Any:
    """
    Load and cache the crowd model (sklearn HistGradientBoostingRegressor).

    Raises CrowdModelUnavailableError on any failure - missing file,
    corrupt pickle, incompatible library version, etc. Caller (PredictionService)
    decides whether to fall back to mock crowding; this function never
    hides the underlying error, it just wraps it so the caller doesn't
    need to know about joblib/sklearn exception types.
    """
    if not _MODEL_PATH.exists():
        raise CrowdModelUnavailableError(f"Model file not found at {_MODEL_PATH}")

    try:
        import joblib
    except ImportError as exc:
        raise CrowdModelUnavailableError(
            "joblib is not installed - add it to requirements.txt"
        ) from exc

    try:
        model = joblib.load(_MODEL_PATH)
    except Exception as exc:  # genuinely broad: corrupt file, version mismatch, etc.
        logger.error("Failed to load crowd model from %s: %s", _MODEL_PATH, exc)
        raise CrowdModelUnavailableError(f"Failed to load crowd model: {exc}") from exc

    expected_features = getattr(model, "n_features_in_", None)
    if expected_features is not None and expected_features != 8:
        raise CrowdModelUnavailableError(
            f"Loaded model expects {expected_features} features, but the "
            "feature schema in app.ml.features defines 8. Model/schema "
            "are out of sync - do not use."
        )

    return model
