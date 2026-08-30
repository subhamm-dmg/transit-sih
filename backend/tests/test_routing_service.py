"""
Tests for the routing layer: RoutingProvider interface, MockRoutingProvider
(parity with the pre-refactor mock behavior), the GoogleRoutesProvider stub,
and the RoutingService facade that selects between them.

Fully offline - no internet, no API keys.
"""

import pytest

from app.services.routing_service import (
    CandidateRoute,
    GoogleRoutesProvider,
    MockRoutingProvider,
    RouteNotFoundError,
    RoutingProvider,
    RoutingService,
)


# ---------------------------------------------------------------------------
# MockRoutingProvider - behavior parity with the original mock RoutingService
# ---------------------------------------------------------------------------


def test_mock_provider_known_pair_returns_expected_routes() -> None:
    provider = MockRoutingProvider()
    routes = provider.get_candidate_routes("Majestic", "Indiranagar")

    assert len(routes) == 3
    ids = {r.route_id for r in routes}
    assert ids == {"R1", "R2", "R3"}
    assert all(isinstance(r, CandidateRoute) for r in routes)


def test_mock_provider_is_case_and_whitespace_insensitive() -> None:
    provider = MockRoutingProvider()
    a = provider.get_candidate_routes("  Majestic ", "INDIRANAGAR")
    b = provider.get_candidate_routes("majestic", "indiranagar")
    assert [r.route_id for r in a] == [r.route_id for r in b]


def test_mock_provider_unknown_pair_falls_back() -> None:
    provider = MockRoutingProvider()
    routes = provider.get_candidate_routes("Some Stop", "Another Stop")
    assert len(routes) == 2  # _FALLBACK_ROUTES
    assert {r.route_id for r in routes} == {"R1", "R2"}


def test_mock_provider_same_origin_and_destination_raises() -> None:
    provider = MockRoutingProvider()
    with pytest.raises(RouteNotFoundError):
        provider.get_candidate_routes("Majestic", "majestic")


def test_mock_provider_accepts_departure_time_but_ignores_it() -> None:
    provider = MockRoutingProvider()
    with_time = provider.get_candidate_routes("Majestic", "Indiranagar", "18:00")
    without_time = provider.get_candidate_routes("Majestic", "Indiranagar")
    assert [r.route_id for r in with_time] == [r.route_id for r in without_time]


def test_mock_provider_get_route_by_id() -> None:
    provider = MockRoutingProvider()
    route = provider.get_route_by_id("Majestic", "Indiranagar", "R2")
    assert route is not None
    assert route.route_name == "Metro + Bus"

    missing = provider.get_route_by_id("Majestic", "Indiranagar", "NOPE")
    assert missing is None


def test_mock_provider_known_stops() -> None:
    provider = MockRoutingProvider()
    stops = provider.known_stops()
    assert "majestic" in stops
    assert "indiranagar" in stops


# ---------------------------------------------------------------------------
# Interface compliance
# ---------------------------------------------------------------------------


def test_mock_and_google_providers_implement_routing_provider() -> None:
    assert issubclass(MockRoutingProvider, RoutingProvider)
    assert issubclass(GoogleRoutesProvider, RoutingProvider)


def test_routing_provider_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        RoutingProvider()  # abstract - must be subclassed


# ---------------------------------------------------------------------------
# GoogleRoutesProvider stub
# ---------------------------------------------------------------------------


def test_google_routes_provider_raises_not_implemented() -> None:
    provider = GoogleRoutesProvider()
    with pytest.raises(NotImplementedError):
        provider.get_candidate_routes("Majestic", "Indiranagar", "18:00")


# ---------------------------------------------------------------------------
# RoutingService facade
# ---------------------------------------------------------------------------


def test_routing_service_defaults_to_mock_provider() -> None:
    # No explicit provider passed, no ROUTING_MODE env var set -> default
    # config value ("mock") should be used.
    service = RoutingService()
    assert isinstance(service.provider, MockRoutingProvider)


def test_routing_service_accepts_explicit_provider_override() -> None:
    service = RoutingService(provider=GoogleRoutesProvider())
    assert isinstance(service.provider, GoogleRoutesProvider)
    with pytest.raises(NotImplementedError):
        service.get_candidate_routes("Majestic", "Indiranagar", "18:00")


def test_routing_service_delegates_get_candidate_routes() -> None:
    service = RoutingService(provider=MockRoutingProvider())
    routes = service.get_candidate_routes("Majestic", "Indiranagar", "18:00")
    assert len(routes) == 3


def test_routing_service_get_route_by_id() -> None:
    service = RoutingService(provider=MockRoutingProvider())
    route = service.get_route_by_id("Majestic", "Indiranagar", "R1")
    assert route is not None
    assert route.route_id == "R1"


def test_routing_service_known_stops_passthrough() -> None:
    service = RoutingService(provider=MockRoutingProvider())
    assert "majestic" in service.known_stops()


def test_routing_service_unknown_mode_raises_value_error(monkeypatch) -> None:
    from app.core import config as config_module

    monkeypatch.setenv("ROUTING_MODE", "not_a_real_mode")
    config_module.get_settings.cache_clear()
    try:
        with pytest.raises(ValueError):
            RoutingService()
    finally:
        monkeypatch.delenv("ROUTING_MODE", raising=False)
        config_module.get_settings.cache_clear()
