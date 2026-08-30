"""
PredictionService — ETA, delay, and crowding predictions.

STATUS:
  - predict_crowding: REAL ML (HistGradientBoostingRegressor, crowd_model.pkl),
    with an automatic fallback to the old deterministic mock logic if the
    model can't be loaded at runtime.
  - predict_eta / predict_delay: STILL MOCK. The supplied training script
    (ml_test.py) expects `eta_minutes` / `delay_minutes` columns that do not
    exist in the supplied dataset (data/ml/synthetic_transit_data.csv only
    has a `crowd_level` target) - see ml/README.md. Wiring these up needs a
    dataset with those columns; nothing here was silently faked to look
    trained.

Every CrowdingPrediction is tagged with `source` ("ml" or "mock") so
callers/logs can tell which path actually served a given request -
useful since the fallback is automatic and silent to the API caller.

PredictionService can be constructed and called with zero FastAPI/HTTP
involvement (see backend/tests/test_prediction_service.py) and does not
require network access to produce predictions.
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from enum import Enum

from app.ml.crowd_model_loader import CrowdModelUnavailableError, get_crowd_model
from app.ml.features import (
    DEFAULT_CURRENT_DELAY,
    DEFAULT_DISTANCE_KM,
    DEFAULT_TRAFFIC_LEVEL,
    DEFAULT_WEATHER_LEVEL,
    FEATURES,
    CrowdFeatureInputs,
    build_feature_row,
)

logger = logging.getLogger(__name__)


class CrowdLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass(frozen=True)
class CrowdingPrediction:
    crowd_level: CrowdLevel
    crowd_score: int  # 0-100 (API contract - rescaled from the model's 0-1000 output)
    source: str = "mock"  # "ml" or "mock" - which path actually produced this


# Kept for RecommendationService's existing `from ... import PREDICTION_MODE`.
# ETA/delay are still mock; crowding is ml-with-fallback - "hybrid" reflects
# that this is no longer a pure mock backend, without overclaiming full ML.
# NOTE for the API/integration owner: this is a static, import-time constant,
# so it can't reflect a runtime crowd-model load failure. If you want
# metadata.prediction_mode to be accurate when the fallback kicks in, read
# `PredictionService().crowding_source` per-request instead of this constant.
PREDICTION_MODE = "hybrid"


class PredictionService:
    """ETA/delay: deterministic mock. Crowding: real ML model with mock fallback."""

    def __init__(self) -> None:
        self._crowd_model = None
        self._crowd_model_error: str | None = None
        try:
            self._crowd_model = get_crowd_model()
        except CrowdModelUnavailableError as exc:
            # Not hidden: logged loudly, and every prediction this instance
            # serves will carry source="mock" so it's visible downstream too.
            logger.error("Crowd model unavailable, falling back to mock crowding: %s", exc)
            self._crowd_model_error = str(exc)

    @property
    def crowding_source(self) -> str:
        return "ml" if self._crowd_model is not None else "mock"

    def predict_eta(
        self, base_travel_minutes: int, route_id: str, departure_time: str
    ) -> int:
        """
        Predict ETA (minutes) for a candidate route. Still mock - see
        module docstring for why (no eta_minutes target in the training data).
        """
        offset = self._deterministic_offset(route_id, departure_time, spread=4)
        return max(1, base_travel_minutes + offset)

    def predict_delay(self, route_id: str, departure_time: str) -> int:
        """
        Predict delay (minutes) for a candidate route. Still mock - see
        module docstring for why (no delay_minutes target in the training data).
        """
        return self._deterministic_offset(route_id, departure_time, spread=10, min_value=0)

    def predict_crowding(
        self,
        route_id: str,
        departure_time: str,
        transfers: int,
        *,
        distance_km: float | None = None,
        traffic_level: float | None = None,
        weather_level: float | None = None,
        current_delay: float | None = None,
        reference_date: datetime.date | None = None,
    ) -> CrowdingPrediction:
        """
        Predict crowding for a candidate route.

        Signature is backward compatible: RecommendationService's existing
        call site (route_id, departure_time, transfers) keeps working
        unchanged. The new keyword-only args let a caller pass real context
        the model was trained on when it has it; anything omitted falls
        back to a sensible default (see app.ml.features) rather than
        crashing - the API currently has no distance_km, traffic, weather,
        or a real calendar date to give us, so today's calls will mostly
        run on defaults for those specific fields until that data is wired
        up (see ml/README.md "Known integration gap").

        `transfers` isn't a training feature; it's folded into the crowd
        score afterwards (extra transfers -> more crowding exposure), same
        adjustment the old mock logic made.
        """
        hour = self._parse_hour(departure_time)
        day_of_week = (reference_date or datetime.date.today()).weekday()

        if self._crowd_model is not None:
            try:
                raw_score = self._predict_with_model(
                    hour=hour,
                    day_of_week=day_of_week,
                    distance_km=distance_km,
                    traffic_level=traffic_level,
                    weather_level=weather_level,
                    current_delay=current_delay,
                )
                score = min(100, max(0, round(raw_score / 10) + transfers * 3))
                return CrowdingPrediction(
                    crowd_level=self._level_for_score(score), crowd_score=score, source="ml"
                )
            except Exception as exc:  # model call itself failed at inference time
                logger.error("Crowd model inference failed, using mock for this call: %s", exc)

        # Fallback: original deterministic mock logic (model missing or errored).
        return self._mock_crowding(route_id, departure_time, transfers, hour)

    # -- ML path -------------------------------------------------------

    def _predict_with_model(
        self,
        *,
        hour: int,
        day_of_week: int,
        distance_km: float | None,
        traffic_level: float | None,
        weather_level: float | None,
        current_delay: float | None,
    ) -> float:
        import pandas as pd

        inputs = CrowdFeatureInputs(
            distance_km=distance_km if distance_km is not None else DEFAULT_DISTANCE_KM,
            hour=hour,
            day_of_week=day_of_week,
            traffic_level=traffic_level if traffic_level is not None else DEFAULT_TRAFFIC_LEVEL,
            weather_level=weather_level if weather_level is not None else DEFAULT_WEATHER_LEVEL,
            current_delay=current_delay if current_delay is not None else DEFAULT_CURRENT_DELAY,
        )
        row = build_feature_row(inputs)
        frame = pd.DataFrame([row])[FEATURES]  # enforce exact training column order
        prediction = self._crowd_model.predict(frame)[0]
        return float(min(1000.0, max(0.0, prediction)))

    # -- mock fallback ---------------------------------------------------

    def _mock_crowding(
        self, route_id: str, departure_time: str, transfers: int, hour: int
    ) -> CrowdingPrediction:
        peak_bonus = 25 if hour in (8, 9, 18, 19) else 0
        base = self._deterministic_offset(route_id, departure_time, spread=60, min_value=10)
        score = min(100, base + peak_bonus + transfers * 5)
        return CrowdingPrediction(
            crowd_level=self._level_for_score(score), crowd_score=score, source="mock"
        )

    @staticmethod
    def _level_for_score(score: int) -> CrowdLevel:
        if score < 30:
            return CrowdLevel.LOW
        if score < 55:
            return CrowdLevel.MODERATE
        if score < 80:
            return CrowdLevel.HIGH
        return CrowdLevel.VERY_HIGH

    # -- shared helpers ----------------------------------------------------

    @staticmethod
    def _parse_hour(departure_time: str) -> int:
        try:
            return int(departure_time.split(":")[0])
        except (ValueError, IndexError):
            return 12

    @staticmethod
    def _deterministic_offset(
        route_id: str, departure_time: str, spread: int, min_value: int = 0
    ) -> int:
        """
        Small deterministic pseudo-random-looking number derived from
        route_id + departure_time, bounded to [min_value, min_value+spread].
        Same inputs always produce the same output (no real randomness).
        """
        seed_str = f"{route_id}-{departure_time}"
        digest = sum(ord(c) for c in seed_str)
        return min_value + (digest % (spread + 1))
