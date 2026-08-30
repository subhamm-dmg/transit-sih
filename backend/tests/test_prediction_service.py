"""
Tests for the Prediction Engine (PredictionService).

Fully offline - no internet, no API keys, no dependency on the Google
Routes integration (uses RouteInfo directly / RoutingService's mock
network only).
"""

from app.services.prediction_service import (
    LiveSignal,
    PredictionService,
    RouteInfo,
)
from app.services.routing_service import RoutingService


def _mock_route_info(**overrides) -> RouteInfo:
    defaults = dict(
        route_id="R1",
        base_duration_minutes=30,
        transfers=0,
        departure_time="12:00",
    )
    defaults.update(overrides)
    return RouteInfo(**defaults)


def test_off_peak_route_has_lower_delay_than_peak() -> None:
    ps = PredictionService()
    route = _mock_route_info()

    off_peak = ps.predict(route, departure_time="14:00", is_weekend=False)
    peak = ps.predict(route, departure_time="18:00", is_weekend=False)

    assert off_peak.delay_minutes < peak.delay_minutes
    assert off_peak.crowd_score < peak.crowd_score


def test_weekday_peak_route() -> None:
    ps = PredictionService()
    route = _mock_route_info()
    result = ps.predict(route, departure_time="18:30", is_weekend=False)

    assert result.eta_minutes > 0
    assert result.crowd_level.value in ("MODERATE", "HIGH", "VERY_HIGH")
    assert result.prediction_mode == "heuristic"


def test_weekend_route_has_lower_crowding_than_weekday_peak() -> None:
    ps = PredictionService()
    route = _mock_route_info()

    weekend = ps.predict(route, departure_time="18:00", is_weekend=True)
    weekday_peak = ps.predict(route, departure_time="18:00", is_weekend=False)

    assert weekend.crowd_score < weekday_peak.crowd_score


def test_high_crowd_conditions() -> None:
    ps = PredictionService()
    route = _mock_route_info(
        transfers=2, involves_major_hub=True, ridership_class="high_demand"
    )
    result = ps.predict(route, departure_time="18:00", is_weekend=False)

    assert result.crowd_score >= 56
    assert result.crowd_level.value in ("HIGH", "VERY_HIGH")


def test_low_crowd_conditions() -> None:
    ps = PredictionService()
    route = _mock_route_info(transfers=0)
    result = ps.predict(route, departure_time="15:00", is_weekend=True)

    assert result.crowd_score <= 30
    assert result.crowd_level.value == "LOW"


def test_missing_traffic_data_falls_back_gracefully() -> None:
    ps = PredictionService()
    route = _mock_route_info()
    result = ps.predict(
        route, departure_time="18:00", is_weekend=False, traffic_info=None, weather_info=None
    )

    # Must not raise, and must clearly report it used pure heuristics.
    assert result.data_source == "heuristic"
    assert result.eta_minutes > 0


def test_missing_weather_data_falls_back_gracefully() -> None:
    ps = PredictionService()
    route = _mock_route_info()

    class FakeTraffic:
        level = "MODERATE"
        delay_factor = 1.1

    result = ps.predict(
        route,
        departure_time="18:00",
        is_weekend=False,
        traffic_info=FakeTraffic(),
        weather_info=None,
    )

    assert "traffic" in result.data_source
    assert "weather" not in result.data_source
    assert result.eta_minutes > 0


def test_prediction_confidence_never_exceeds_bounds() -> None:
    ps = PredictionService()
    route = _mock_route_info()
    result = ps.predict(route, departure_time="18:00", is_weekend=False)

    assert 0.0 <= result.eta_confidence <= 1.0
    assert 0.0 <= result.delay_confidence <= 1.0
    assert 0.0 <= result.crowd_confidence <= 1.0


def test_confidence_increases_with_more_data() -> None:
    ps = PredictionService()
    route = _mock_route_info()

    class FakeTraffic:
        level = "HEAVY"
        delay_factor = 1.25

    class FakeWeather:
        condition = "RAIN"

    no_data = ps.predict(route, departure_time="18:00", is_weekend=False)
    with_data = ps.predict(
        route,
        departure_time="18:00",
        is_weekend=False,
        traffic_info=FakeTraffic(),
        weather_info=FakeWeather(),
    )

    assert with_data.eta_confidence > no_data.eta_confidence


def test_deterministic_results() -> None:
    ps = PredictionService()
    route = _mock_route_info()

    result_a = ps.predict(route, departure_time="18:00", is_weekend=False)
    result_b = ps.predict(route, departure_time="18:00", is_weekend=False)

    assert result_a.eta_minutes == result_b.eta_minutes
    assert result_a.delay_minutes == result_b.delay_minutes
    assert result_a.crowd_score == result_b.crowd_score


def test_live_signal_overrides_heuristic_delay() -> None:
    ps = PredictionService()
    route = _mock_route_info()
    signal = LiveSignal(delay_override_minutes=20, note="Unexpected road closure")

    result = ps.predict(route, departure_time="14:00", is_weekend=False, live_signal=signal)

    assert result.delay_minutes == 20
    assert "live_signal" in result.data_source


def test_route_info_adapts_from_mock_routing_candidate() -> None:
    # Confirms PredictionService can consume RoutingService's existing
    # mock CandidateRoute objects via the generic RouteInfo adapter,
    # without importing RoutingService's class directly.
    routing_service = RoutingService()
    candidates = routing_service.get_candidate_routes("Majestic", "Indiranagar")
    assert candidates

    ps = PredictionService()
    for candidate in candidates:
        route_info = RouteInfo.from_candidate(candidate)
        result = ps.predict(route_info, departure_time="18:00", is_weekend=False)
        assert result.eta_minutes > 0
        assert result.crowd_level.value in ("LOW", "MODERATE", "HIGH", "VERY_HIGH")
