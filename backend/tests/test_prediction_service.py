"""
Tests for PredictionService's crowd prediction.

Fully offline - no FastAPI TestClient, no network access. Only imports
app.services.prediction_service and app.ml.*.
"""

import datetime

import pytest

from app.ml.crowd_model_loader import get_crowd_model
from app.ml.features import FEATURES
from app.services.prediction_service import CrowdLevel, PredictionService


def test_model_loads() -> None:
    """1. model loads"""
    model = get_crowd_model()
    assert model is not None
    assert getattr(model, "n_features_in_", None) == len(FEATURES)


def test_service_reports_ml_source_when_model_available() -> None:
    service = PredictionService()
    assert service.crowding_source == "ml"


def test_valid_input_produces_a_prediction() -> None:
    """2. valid input produces a prediction, 3. expected type/range"""
    service = PredictionService()
    result = service.predict_crowding(
        route_id="R1",
        departure_time="09:00",
        transfers=1,
        distance_km=10.0,
        traffic_level=6,
        weather_level=1,
        current_delay=5.0,
        reference_date=datetime.date(2026, 8, 31),  # a Monday
    )
    assert isinstance(result.crowd_score, int)
    assert 0 <= result.crowd_score <= 100
    assert isinstance(result.crowd_level, CrowdLevel)
    assert result.source == "ml"


def test_missing_optional_context_does_not_crash() -> None:
    """4. missing optional context does not crash - defaults kick in."""
    service = PredictionService()
    result = service.predict_crowding(route_id="R2", departure_time="18:30", transfers=0)
    assert 0 <= result.crowd_score <= 100
    assert isinstance(result.crowd_level, CrowdLevel)


def test_rush_hour_scores_higher_than_off_peak_all_else_equal() -> None:
    """Sanity check that rush-hour context increases predicted crowding."""
    service = PredictionService()
    common = dict(
        route_id="R1",
        transfers=0,
        distance_km=10.0,
        traffic_level=5,
        weather_level=1,
        current_delay=5.0,
        reference_date=datetime.date(2026, 8, 31),
    )
    rush = service.predict_crowding(departure_time="09:00", **common)
    off_peak = service.predict_crowding(departure_time="14:00", **common)
    assert rush.crowd_score >= off_peak.crowd_score


def test_feature_ordering_matches_model() -> None:
    """5. feature ordering matches the model."""
    model = get_crowd_model()
    assert list(model.feature_names_in_) == FEATURES


def test_prediction_service_usable_without_fastapi() -> None:
    """6. PredictionService can be called independently of FastAPI."""
    service = PredictionService()
    eta = service.predict_eta(base_travel_minutes=30, route_id="R1", departure_time="09:00")
    delay = service.predict_delay(route_id="R1", departure_time="09:00")
    crowding = service.predict_crowding(route_id="R1", departure_time="09:00", transfers=0)
    assert eta > 0
    assert delay >= 0
    assert isinstance(crowding.crowd_level, CrowdLevel)


def test_model_load_failure_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fallback path: if the model can't load, crowding still works via mock."""
    import app.services.prediction_service as ps

    def _boom() -> None:
        raise ps.CrowdModelUnavailableError("simulated failure")

    monkeypatch.setattr(ps, "get_crowd_model", _boom)
    service = PredictionService()
    assert service.crowding_source == "mock"

    result = service.predict_crowding(route_id="R1", departure_time="09:00", transfers=0)
    assert result.source == "mock"
    assert 0 <= result.crowd_score <= 100
