"""
ml/inference.py — Production ML Inference Engine for TransitAI.

Loads the trained model parameters and provides fast, deterministic inference for:
- ETA Prediction (minutes)
- Delay Prediction (minutes + risk probability)
- Crowding Prediction (score + crowd level category)
"""

import json
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
import numpy as np


class CrowdLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class DelayRisk(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class MLPredictionOutput:
    eta_minutes: int
    delay_minutes: int
    delay_risk: DelayRisk
    delay_probability: float
    crowd_score: int
    crowd_level: CrowdLevel
    confidence: float
    features_used: dict


class MLInferenceEngine:
    """Inference engine executing Ridge Non-Linear Transit Ensemble."""

    _instance: Optional["MLInferenceEngine"] = None

    def __init__(self, model_path: Optional[Path] = None):
        if model_path is None:
            model_path = Path(__file__).resolve().parent / "models" / "transit_models.json"

        self.model_path = model_path
        self.is_loaded = False
        self.eta_weights = None
        self.delay_weights = None
        self.crowd_weights = None
        self._load_model()

    @classmethod
    def get_instance(cls) -> "MLInferenceEngine":
        if cls._instance is None:
            cls._instance = MLInferenceEngine()
        return cls._instance

    def _load_model(self):
        try:
            if self.model_path.exists():
                with open(self.model_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.eta_weights = np.array(data["models"]["eta"]["weights"])
                self.delay_weights = np.array(data["models"]["delay"]["weights"])
                self.crowd_weights = np.array(data["models"]["crowding"]["weights"])
                self.is_loaded = True
            else:
                # Fallback to analytical model if file not yet generated
                self._init_analytical_fallbacks()
        except Exception as err:
            print(f"[MLInferenceEngine] Warning loading model: {err}. Using analytical fallbacks.")
            self._init_analytical_fallbacks()

    def _init_analytical_fallbacks(self):
        self.is_loaded = True
        # Analytical defaults
        self.eta_weights = np.zeros(16)
        self.eta_weights[0] = 0.0
        self.eta_weights[1] = 1.0  # base travel time coefficient
        self.delay_weights = np.zeros(16)
        self.crowd_weights = np.zeros(16)

    def _build_feature_vector(
        self,
        base_travel_minutes: float,
        distance_km: float,
        num_stops: int,
        mode_bus_ratio: float,
        transfers: int,
        hour: int,
        is_weekend: int,
        traffic_factor: float,
        rain_mm: float,
    ) -> np.ndarray:
        hour_sin = math.sin(2 * math.pi * hour / 24.0)
        hour_cos = math.cos(2 * math.pi * hour / 24.0)
        is_peak = 1.0 if ((8 <= hour <= 10) or (17 <= hour <= 20)) else 0.0
        traffic_bus_interact = (traffic_factor - 1.0) * mode_bus_ratio
        rain_bus_interact = (rain_mm / 10.0) * mode_bus_ratio

        return np.array([
            1.0,  # Intercept
            base_travel_minutes,
            distance_km,
            float(num_stops),
            float(mode_bus_ratio),
            float(transfers),
            hour_sin,
            hour_cos,
            float(is_weekend),
            traffic_factor,
            rain_mm,
            is_peak,
            traffic_bus_interact,
            rain_bus_interact,
            (base_travel_minutes * traffic_bus_interact),
            (float(num_stops) * traffic_bus_interact),
        ])

    def predict(
        self,
        base_travel_minutes: int,
        distance_km: float = 12.0,
        num_stops: int = 14,
        mode_bus_ratio: float = 1.0,
        transfers: int = 0,
        departure_time: str = "09:00",
        traffic_factor: float = 1.15,
        rain_mm: float = 0.0,
        is_weekend: bool = False,
    ) -> MLPredictionOutput:
        try:
            hour = int(departure_time.split(":")[0])
        except (ValueError, IndexError):
            hour = 9

        feat = self._build_feature_vector(
            base_travel_minutes=float(base_travel_minutes),
            distance_km=distance_km,
            num_stops=num_stops,
            mode_bus_ratio=mode_bus_ratio,
            transfers=transfers,
            hour=hour,
            is_weekend=1 if is_weekend else 0,
            traffic_factor=traffic_factor,
            rain_mm=rain_mm,
        )

        if self.eta_weights is not None and len(self.eta_weights) == len(feat):
            raw_eta = float(np.dot(feat, self.eta_weights))
            raw_delay = float(np.dot(feat, self.delay_weights))
            raw_crowd = float(np.dot(feat, self.crowd_weights))
        else:
            # Fallback heuristic
            peak = 1.3 if (8 <= hour <= 10 or 17 <= hour <= 20) else 1.0
            raw_delay = max(0.0, (traffic_factor - 1.0) * 15 * mode_bus_ratio + transfers * 3.0)
            raw_eta = max(5.0, base_travel_minutes + raw_delay)
            raw_crowd = 25.0 * peak + (traffic_factor - 1.0) * 40.0

        delay_minutes = max(0, int(round(raw_delay)))
        eta_minutes = max(max(1, base_travel_minutes), int(round(raw_eta)))
        crowd_score = max(5, min(99, int(round(raw_crowd))))

        # Delay risk category & probability
        if delay_minutes <= 2:
            delay_risk = DelayRisk.LOW
            delay_prob = 0.15
        elif delay_minutes <= 6:
            delay_risk = DelayRisk.MODERATE
            delay_prob = 0.45
        elif delay_minutes <= 12:
            delay_risk = DelayRisk.HIGH
            delay_prob = 0.78
        else:
            delay_risk = DelayRisk.CRITICAL
            delay_prob = 0.92

        # Crowding Level category
        if crowd_score < 35:
            crowd_level = CrowdLevel.LOW
        elif crowd_score < 65:
            crowd_level = CrowdLevel.MODERATE
        elif crowd_score < 85:
            crowd_level = CrowdLevel.HIGH
        else:
            crowd_level = CrowdLevel.VERY_HIGH

        # Confidence: Metro is higher confidence (dedicated track), extreme weather lowers confidence
        base_confidence = 0.92 if mode_bus_ratio < 0.3 else 0.84
        weather_penalty = min(0.12, (rain_mm / 25.0) * 0.12)
        traffic_penalty = min(0.08, max(0.0, (traffic_factor - 1.4) * 0.15))
        confidence = round(max(0.60, min(0.98, base_confidence - weather_penalty - traffic_penalty)), 2)

        return MLPredictionOutput(
            eta_minutes=eta_minutes,
            delay_minutes=delay_minutes,
            delay_risk=delay_risk,
            delay_probability=delay_prob,
            crowd_score=crowd_score,
            crowd_level=crowd_level,
            confidence=confidence,
            features_used={
                "base_travel_minutes": base_travel_minutes,
                "distance_km": distance_km,
                "num_stops": num_stops,
                "mode_bus_ratio": mode_bus_ratio,
                "transfers": transfers,
                "hour": hour,
                "traffic_factor": round(traffic_factor, 2),
                "rain_mm": rain_mm,
            },
        )
