"""
RoutingService — generates candidate journeys between two stops.

Tonight this uses a small, deterministic, hardcoded mock transit network
(stops + routes + travel/wait times + transfers). No real routing
algorithm, no GTFS parsing.

Swap-out plan for tomorrow:
    Replace `_MOCK_STOPS` / `_MOCK_ROUTES` and `get_candidate_routes()`
    with GTFS-based lookups. The public method signatures below are the
    contract the rest of the app (API layer, scoring) depends on — keep
    them stable and the rest of the system won't need to change.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MockLeg:
    """One leg of a candidate journey."""

    mode: str  # e.g. "BUS", "METRO"
    line: str  # e.g. "500D", "Purple Line"
    travel_minutes: int


@dataclass(frozen=True)
class CandidateRoute:
    """A full candidate journey from origin to destination."""

    route_id: str
    route_name: str
    legs: list[MockLeg]
    base_travel_minutes: int
    base_waiting_minutes: int
    transfers: int


# ---------------------------------------------------------------------------
# Mock transit network
# ---------------------------------------------------------------------------
# A handful of well-known Bengaluru-ish stop names so demo output looks
# sensible. Purely illustrative — replace with real GTFS stops tomorrow.

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


class RouteNotFoundError(Exception):
    """Raised when no candidate route can be generated for the request."""


class RoutingService:
    """Generates candidate journeys for a given origin/destination pair."""

    def known_stops(self) -> set[str]:
        return set(_MOCK_STOPS)

    def get_candidate_routes(self, origin: str, destination: str) -> list[CandidateRoute]:
        """
        Return candidate routes between origin and destination.

        Tonight: looks up a small static table, falling back to a generic
        two-option network for any unseen stop pair. This keeps the demo
        working for arbitrary stop names typed by judges.
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
