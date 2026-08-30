"""
Feature schema for the crowd prediction model.

This is the SINGLE place that defines which columns the crowd model
expects and how they're derived. crowd_model.pkl was trained on exactly
these 8 columns, in this order (verified against the model's
`feature_names_in_`): don't add/remove/reorder without retraining.

    route + context -> feature vector -> model -> crowd prediction

`ml/train_crowd_model.py` (repo root, offline training script) imports
this same module so the training-time and serving-time feature logic
can never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass

# Order matters - must match crowd_model.pkl's feature_names_in_ exactly.
FEATURES: list[str] = [
    "distance_km",
    "time_of_day",
    "day_of_week",
    "traffic_level",
    "weather_level",
    "current_delay",
    "is_weekend",
    "is_rush_hour",
]

# Sensible fallback values for context the API doesn't currently collect
# (see PredictionService docstring for which fields these are and why).
# Taken from the synthetic training data's median/mode so an unspecified
# value lands near the "typical" row rather than an extreme one.
DEFAULT_DISTANCE_KM = 8.0
DEFAULT_TRAFFIC_LEVEL = 5  # 0-10 scale in training data, ~median
DEFAULT_WEATHER_LEVEL = 1  # 0-5 scale in training data, mode is clear/mild
DEFAULT_CURRENT_DELAY = 0.0


def is_weekend(day_of_week: int) -> int:
    """0=Mon .. 6=Sun. Matches the derivation used to train the model."""
    return int(day_of_week in (5, 6))


def is_rush_hour(hour: int) -> int:
    """Matches the derivation used to train the model."""
    return int(8 <= hour <= 10 or 17 <= hour <= 20)


@dataclass(frozen=True)
class CrowdFeatureInputs:
    """Raw inputs before derived columns (is_weekend/is_rush_hour) are added."""

    distance_km: float
    hour: int
    day_of_week: int
    traffic_level: float
    weather_level: float
    current_delay: float


def build_feature_row(inputs: CrowdFeatureInputs) -> dict[str, float]:
    """Build one feature row (dict, in FEATURES order) for the crowd model."""
    return {
        "distance_km": inputs.distance_km,
        "time_of_day": inputs.hour,
        "day_of_week": inputs.day_of_week,
        "traffic_level": inputs.traffic_level,
        "weather_level": inputs.weather_level,
        "current_delay": inputs.current_delay,
        "is_weekend": is_weekend(inputs.day_of_week),
        "is_rush_hour": is_rush_hour(inputs.hour),
    }
