"""
backend/app/services/prediction_service.py — ML Prediction Service.

Integrates the trained Machine Learning inference engine with real-time weather
and traffic telemetry to provide high-precision ETA, Delay, and Crowding predictions.
"""

from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any
import datetime

# Ensure project root is on sys.path for ml imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.inference import MLInferenceEngine, MLPredictionOutput, CrowdLevel, DelayRisk
from app.services.weather_service import WeatherService, WeatherInfo
from app.services.traffic_service import TrafficService, TrafficInfo
from app.ml.crowd_model_loader import get_crowd_model, CrowdModelUnavailableError

PREDICTION_MODE = "ml-production"


@dataclass(frozen=True)
class CrowdingPrediction:
    crowd_level: CrowdLevel
    crowd_score: int
    source: str = "ml"


@dataclass(frozen=True)
class PredictionResult:
    eta_minutes: int
    delay_minutes: int
    delay_risk: str
    delay_probability: float
    crowd_score: int
    crowd_level: CrowdLevel
    confidence: float
    weather_condition: str
    traffic_level: str


class PredictionService:
    """Production ML Prediction Service combining GTFS features, ML inference, and live telemetry."""

    def __init__(
        self,
        ml_engine: Optional[MLInferenceEngine] = None,
        weather_service: Optional[WeatherService] = None,
        traffic_service: Optional[TrafficService] = None,
    ):
        self.ml_engine = ml_engine or MLInferenceEngine.get_instance()
        self.weather_service = weather_service or WeatherService()
        self.traffic_service = traffic_service or TrafficService()
        try:
            get_crowd_model()
            self.crowding_source = "ml"
        except CrowdModelUnavailableError:
            self.crowding_source = "mock"
        except Exception:
            self.crowding_source = "mock"

    def predict_journey(
        self,
        base_travel_minutes: int,
        distance_km: float = 12.0,
        num_stops: int = 14,
        mode_bus_ratio: float = 1.0,
        transfers: int = 0,
        departure_time: str = "09:00",
        location: str = "Delhi",
    ) -> PredictionResult:
        """
        Executes end-to-end ML inference for a candidate journey.
        """
        weather: WeatherInfo = self.weather_service.get_weather(location=location, departure_time=departure_time)
        traffic: TrafficInfo = self.traffic_service.get_traffic_level(stop_or_area=location, departure_time=departure_time)

        ml_out: MLPredictionOutput = self.ml_engine.predict(
            base_travel_minutes=base_travel_minutes,
            distance_km=distance_km,
            num_stops=num_stops,
            mode_bus_ratio=mode_bus_ratio,
            transfers=transfers,
            departure_time=departure_time,
            traffic_factor=traffic.congestion_factor,
            rain_mm=weather.rain_mm,
        )

        return PredictionResult(
            eta_minutes=ml_out.eta_minutes,
            delay_minutes=ml_out.delay_minutes,
            delay_risk=ml_out.delay_risk.value,
            delay_probability=ml_out.delay_probability,
            crowd_score=ml_out.crowd_score,
            crowd_level=ml_out.crowd_level,
            confidence=ml_out.confidence,
            weather_condition=weather.condition.value,
            traffic_level=traffic.level.value,
        )

    def predict_eta(self, base_travel_minutes: int, route_id: str = "R1", departure_time: str = "09:00") -> int:
        res = self.predict_journey(base_travel_minutes=base_travel_minutes, departure_time=departure_time)
        return res.eta_minutes

    def predict_delay(self, route_id: str = "R1", departure_time: str = "09:00") -> int:
        res = self.predict_journey(base_travel_minutes=30, departure_time=departure_time)
        return res.delay_minutes

    def predict_crowding(
        self,
        route_id: str = "R1",
        departure_time: str = "09:00",
        transfers: int = 0,
        distance_km: float = 10.0,
        traffic_level: Any = None,
        weather_level: Any = None,
        current_delay: float = 0.0,
        reference_date: Optional[datetime.date] = None,
    ) -> CrowdingPrediction:
        res = self.predict_journey(
            base_travel_minutes=30,
            distance_km=distance_km,
            transfers=transfers,
            departure_time=departure_time,
        )
        return CrowdingPrediction(
            crowd_level=res.crowd_level,
            crowd_score=res.crowd_score,
            source=self.crowding_source,
        )
