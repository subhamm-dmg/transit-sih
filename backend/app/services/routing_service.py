"""
RoutingService — generates candidate journeys between two stops.

Real Routing Engine Integration (this revision):
    RoutingService is now a thin FACADE that selects a RoutingProvider
    implementation based on config (`ROUTING_MODE`, see app/core/config.py)
    and delegates to it. The rest of the app (RecommendationService,
    PredictionService, the API layer) only ever talks to RoutingService's
    public methods - it never knows or cares which provider is behind it.

    - MockRoutingProvider: today's small deterministic hardcoded network
      (unchanged behavior from before this refactor).
    - GoogleRoutesProvider: a STUB for tomorrow's Google Routes API
      integration. Not implemented yet on purpose - no API key, no
      network call. Raises NotImplementedError with a clear message if
      ever selected and called, so the app still starts up fine even
      with ROUTING_MODE misconfigured; it just fails loudly on first use.

    Adding a real provider later = write a new class implementing
    RoutingProvider + flip ROUTING_MODE. Nothing else in the app changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import get_settings


@dataclass(frozen=True)
class MockLeg:
    """One leg of a candidate journey."""

    mode: str  # e.g. "BUS", "METRO"
    line: str  # e.g. "500D", "Purple Line"
    travel_minutes: int


@dataclass(frozen=True)
class CandidateRoute:
    """
    A full candidate journey from origin to destination.

    This is the shared contract every RoutingProvider must return -
    PredictionService and RecommendationService only ever see this shape,
    regardless of which provider produced it.
    """

    route_id: str
    route_name: str
    legs: list[MockLeg]
    base_travel_minutes: int
    base_waiting_minutes: int
    transfers: int


class RouteNotFoundError(Exception):
    """Raised when no candidate route can be generated for the request."""


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------


class RoutingProvider(ABC):
    """
    Interface every routing backend (mock, Google Routes, GTFS, ...) must
    implement. Keeping provider-specific logic behind this interface is
    the whole point of this refactor - RoutingService (and everything
    downstream of it) depends only on this shape, never on a concrete
    provider.
    """

    @abstractmethod
    def get_candidate_routes(
        self, origin: str, destination: str, departure_time: str = ""
    ) -> list[CandidateRoute]:
        """
        Return candidate routes between origin and destination.

        `departure_time` (HH:MM) is accepted by every provider - real
        transit routing APIs need it for accurate ETAs - even though
        today's mock provider ignores it. Raise RouteNotFoundError if no
        candidates can be produced (e.g. same origin/destination).
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Mock provider (today's network - unchanged behavior)
# ---------------------------------------------------------------------------
# A handful of well-known Bengaluru-ish stop names so demo output looks
# sensible. Purely illustrative - replace with real GTFS stops later.

_MOCK_STOPS: set[str] = {
    "majestic",
    "indiranagar",
    "koramangala",
    "whitefield",
    "electronic city",
    "mg road",
    "silk board",
    "hebbal",
    "yeshwanthpur",
    "btm layout",
}

# Candidate routes are keyed by a normalized (from, to) pair.
# Each entry is a list of CandidateRoute objects - the small "network".
_MOCK_ROUTES: dict[tuple[str, str], list[CandidateRoute]] = {
    ("majestic", "indiranagar"): [
        CandidateRoute(
            route_id="R1",
            route_name="Bus 500D",
            legs=[MockLeg(mode="BUS", line="500D", travel_minutes=35)],
            base_travel_minutes=35,
            base_waiting_minutes=3,
            transfers=0,
        ),
        CandidateRoute(
            route_id="R2",
            route_name="Metro + Bus",
            legs=[
                MockLeg(mode="METRO", line="Purple Line", travel_minutes=22),
                MockLeg(mode="BUS", line="201", travel_minutes=14),
            ],
            base_travel_minutes=36,
            base_waiting_minutes=5,
            transfers=1,
        ),
        CandidateRoute(
            route_id="R3",
            route_name="Metro + Walk",
            legs=[MockLeg(mode="METRO", line="Purple Line", travel_minutes=25)],
            base_travel_minutes=25,
            base_waiting_minutes=6,
            transfers=0,
        ),
    ],
}

# Generic fallback network used for any (from, to) pair not explicitly
# defined above, so the demo never dead-ends on an unknown stop pair.
_FALLBACK_ROUTES: list[CandidateRoute] = [
    CandidateRoute(
        route_id="R1",
        route_name="Direct Bus",
        legs=[MockLeg(mode="BUS", line="Express", travel_minutes=40)],
        base_travel_minutes=40,
        base_waiting_minutes=4,
        transfers=0,
    ),
    CandidateRoute(
        route_id="R2",
        route_name="Metro + Bus",
        legs=[
            MockLeg(mode="METRO", line="Green Line", travel_minutes=20),
            MockLeg(mode="BUS", line="Feeder", travel_minutes=15),
        ],
        base_travel_minutes=35,
        base_waiting_minutes=6,
        transfers=1,
    ),
]


class MockRoutingProvider(RoutingProvider):
    """
    Deterministic, offline, hardcoded mock transit network. Identical
    behavior to the pre-refactor RoutingService - only the packaging
    changed (now a RoutingProvider instead of the whole service).
    """

    def known_stops(self) -> set[str]:
        return set(_MOCK_STOPS)

    def get_candidate_routes(
        self, origin: str, destination: str, departure_time: str = ""
    ) -> list[CandidateRoute]:
        """
        Tonight: looks up a small static table, falling back to a generic
        two-option network for any unseen stop pair. This keeps the demo
        working for arbitrary stop names typed by judges. `departure_time`
        is accepted for interface compliance but not used by the mock.
        """
        key = (origin.strip().lower(), destination.strip().lower())

        if key[0] == key[1]:
            raise RouteNotFoundError("Origin and destination must be different stops")

        routes = _MOCK_ROUTES.get(key)
        if routes:
            return routes

        # Fall back to generic mock routes so any input still returns
        # something sensible during the demo.
        return _FALLBACK_ROUTES

    def get_route_by_id(
        self, origin: str, destination: str, route_id: str
    ) -> CandidateRoute | None:
        """Return a single candidate route by id for the given pair, or None."""
        routes = self.get_candidate_routes(origin, destination)
        for route in routes:
            if route.route_id == route_id:
                return route
        return None


# ---------------------------------------------------------------------------
# Google Routes provider (STUB - not implemented)
# ---------------------------------------------------------------------------


class GoogleRoutesProvider(RoutingProvider):
    """
    Placeholder for a future Google Routes API-backed provider.

    INTENTIONALLY NOT IMPLEMENTED. No API key is read or stored here, and
    no network call is made. This class exists only to make the seam
    explicit: whoever wires up Google Routes implements
    `get_candidate_routes()` here, returning the same `CandidateRoute`
    shape the mock provider returns, and nothing else in the app needs to
    change.

    Intended future shape (for whoever implements this):
        - Call Google Routes API with origin/destination/departure_time
          (transit mode).
        - Map each returned transit route into one CandidateRoute:
            route_id       <- generated (e.g. "G1", "G2", ...)
            route_name     <- summary of transit lines used
            legs           <- one MockLeg per transit/walk leg, with
                              mode/line/travel_minutes from the API
            base_travel_minutes <- Google's total duration
            base_waiting_minutes <- derived from first-leg departure delta
            transfers      <- count of transit legs - 1
        - Raise RouteNotFoundError if Google Routes returns zero transit
          routes for the pair.
        - API key would come from `get_settings().GOOGLE_ROUTES_API_KEY`
          (add to config/.env.example when this is actually implemented -
          never hardcode it).
    """

    def get_candidate_routes(
        self, origin: str, destination: str, departure_time: str = ""
    ) -> list[CandidateRoute]:
        raise NotImplementedError(
            "GoogleRoutesProvider is not implemented yet. "
            "Set ROUTING_MODE=mock (the default) to use the offline mock network."
        )


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------

_PROVIDERS: dict[str, type[RoutingProvider]] = {
    "mock": MockRoutingProvider,
    "google": GoogleRoutesProvider,
}


class RoutingService:
    """
    Facade the rest of the app depends on. Selects a RoutingProvider based
    on `settings.ROUTING_MODE` and delegates every call to it. Swapping
    routing backends is a config change (`ROUTING_MODE=mock` / `google`),
    not a code change anywhere else in the app.
    """

    def __init__(self, provider: RoutingProvider | None = None) -> None:
        if provider is not None:
            self.provider = provider
        else:
            mode = get_settings().ROUTING_MODE.strip().lower()
            provider_cls = _PROVIDERS.get(mode)
            if provider_cls is None:
                # Unknown mode -> fail fast and clearly rather than
                # silently guessing, but never crash the app for a typo
                # in an unrelated env var at import time (only when
                # RoutingService is actually constructed).
                raise ValueError(
                    f"Unknown ROUTING_MODE '{mode}'. Supported: {sorted(_PROVIDERS)}"
                )
            self.provider = provider_cls()

    def known_stops(self) -> set[str]:
        """Convenience passthrough - only meaningful for providers that support it."""
        getter = getattr(self.provider, "known_stops", None)
        return getter() if callable(getter) else set()

    def get_candidate_routes(
        self, origin: str, destination: str, departure_time: str = ""
    ) -> list[CandidateRoute]:
        """Return candidate routes between origin and destination."""
        return self.provider.get_candidate_routes(origin, destination, departure_time)

    def get_route_by_id(
        self, origin: str, destination: str, route_id: str
    ) -> CandidateRoute | None:
        """Return a single candidate route by id for the given pair, or None."""
        for route in self.get_candidate_routes(origin, destination):
            if route.route_id == route_id:
                return route
        return None
