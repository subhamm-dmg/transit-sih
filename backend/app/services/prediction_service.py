"""
PredictionService — ETA, delay, and crowding predictions.

Tonight these are DETERMINISTIC MOCK VALUES, not real ML output. Every
result is tagged with prediction_mode="mock" so the API response never
pretends to be a real prediction.

Swap-out plan for tomorrow:
    Replace the bodies of predict_eta / predict_delay / predict_crowding
    with calls into the real ML models. Keep the method signatures and
    the PredictionResult shape the same so RoutingService/scoring and the
    API layer don't need to change.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CrowdLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass(frozen=True)
class CrowdingPrediction:
    crowd_level: CrowdLevel
    crowd_score: int  # 0-100


PREDICTION_MODE = "mock"


class PredictionService:
    """Deterministic mock stand-in for the real ML prediction engine."""

    def predict_eta(
        self, base_travel_minutes: int, route_id: str, departure_time: str
    ) -> int:
        """
        Predict ETA (minutes) for a candidate route.

        Mock rule: base travel time + a small deterministic offset derived
        from the route_id and departure hour, so results vary a bit
        between routes/times without being random (keeps demo stable and
        reproducible).
        """
        offset = self._deterministic_offset(route_id, departure_time, spread=4)
        return max(1, base_travel_minutes + offset)

    def predict_delay(self, route_id: str, departure_time: str) -> int:
        """
        Predict delay (minutes) for a candidate route.

        Mock rule: deterministic 0-10 minute delay based on route_id and
        departure hour. Routes with more legs/transfers tend to model
        slightly higher delay risk upstream in the routing service, not
        here - this stays a pure function of route_id/time.
        """
        return self._deterministic_offset(route_id, departure_time, spread=10, min_value=0)

    def predict_crowding(
        self, route_id: str, departure_time: str, transfers: int
    ) -> CrowdingPrediction:
        """
        Predict crowding for a candidate route.

        Mock rule: deterministic score 0-100 based on route_id, departure
        hour (peak hours score higher), and transfers.
        """
        hour = self._parse_hour(departure_time)
        peak_bonus = 25 if hour in (8, 9, 18, 19) else 0
        base = self._deterministic_offset(route_id, departure_time, spread=60, min_value=10)
        score = min(100, base + peak_bonus + transfers * 5)

        if score < 30:
            level = CrowdLevel.LOW
        elif score < 55:
            level = CrowdLevel.MODERATE
        elif score < 80:
            level = CrowdLevel.HIGH
        else:
            level = CrowdLevel.VERY_HIGH

        return CrowdingPrediction(crowd_level=level, crowd_score=score)

    # -- helpers -----------------------------------------------------------

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
