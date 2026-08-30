"""
RoutingService — generates candidate journeys between two stops.

Architecture:

    API
      ↓
    RecommendationService
      ↓
    RoutingService
      ↓
    GTFSService
      ↓
    Delhi/DTC GTFS data

RoutingService owns the application's route representation.

GTFSService only understands GTFS.

This separation means we can later replace the GTFS implementation with
Google Routes, another routing engine, or a hybrid engine without forcing
RecommendationService / ScoringService to change.

The public CandidateRoute contract remains stable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .gtfs_service import (
    GTFSDirectTrip,
    GTFSService,
)


# ---------------------------------------------------------------------------
# Public route models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MockLeg:
    """
    One leg of a candidate journey.

    Kept as MockLeg for backwards compatibility with the existing
    application contract.

    The name can be renamed later to RouteLeg if the whole codebase
    is migrated.
    """

    mode: str
    line: str
    travel_minutes: int


@dataclass(frozen=True)
class CandidateRoute:
    """
    Public route object consumed by the rest of the backend.
    """

    route_id: str
    route_name: str
    legs: list[MockLeg]
    base_travel_minutes: int
    base_waiting_minutes: int
    transfers: int


class RouteNotFoundError(Exception):
    """Raised when no candidate route can be generated."""


# ---------------------------------------------------------------------------
# RoutingService
# ---------------------------------------------------------------------------


class RoutingService:
    """
    Generates candidate routes using the Delhi GTFS feed.

    Routing strategy:

        1. Validate origin/destination.
        2. Reject same origin and destination.
        3. Try real GTFS direct routing.
        4. If GTFS has a direct route, return GTFS-backed candidates.
        5. If GTFS has no direct route, return deterministic fallback
           candidates so the prototype remains usable.
        6. Keep the CandidateRoute interface stable for downstream
           services.

    This fallback is intentional.

    The current DTC GTFS feed does not necessarily contain a direct
    bus trip between arbitrary user-entered places such as:

        Majestic → Indiranagar

    Therefore, the application must not return HTTP 404 merely because
    the current GTFS feed has no direct trip.

    Later, Google Routes / a graph routing engine can replace the
    fallback implementation without changing the public CandidateRoute
    contract.
    """

    def __init__(
        self,
        gtfs_service: GTFSService | None = None,
        *,
        gtfs_path: str | Path | None = None,
    ) -> None:
        if gtfs_service is not None:
            self.gtfs = gtfs_service
        else:
            self.gtfs = GTFSService(
                feed_path=gtfs_path,
            )

    # ------------------------------------------------------------------
    # Stop API
    # ------------------------------------------------------------------

    def known_stops(self) -> list[str]:
        """
        Return stop names known by the GTFS feed.
        """

        return self._all_stop_names()

    # ------------------------------------------------------------------
    # Candidate routes
    # ------------------------------------------------------------------

    def get_candidate_routes(
        self,
        origin: str,
        destination: str,
    ) -> list[CandidateRoute]:
        """
        Generate candidate journeys from origin to destination.

        Order:

            1. Validate input.
            2. Reject same origin/destination.
            3. Search GTFS for direct trips.
            4. Convert GTFS trips into CandidateRoute objects.
            5. If no GTFS route exists, use deterministic fallback routes.

        The fallback is important for the current prototype because
        the DTC GTFS feed does not contain every possible origin/
        destination combination.
        """

        origin = origin.strip()
        destination = destination.strip()

        # --------------------------------------------------------------
        # Validation
        # --------------------------------------------------------------

        if not origin or not destination:
            raise RouteNotFoundError(
                "Origin and destination are required."
            )

        # Same stop is not a journey.
        #
        # This preserves the existing API/test contract:
        #
        #     Majestic → Majestic
        #
        # should return HTTP 404.
        if origin.casefold() == destination.casefold():
            raise RouteNotFoundError(
                "Origin and destination must be different."
            )

        # --------------------------------------------------------------
        # 1. Try real GTFS routing
        # --------------------------------------------------------------

        try:
            trips = self.gtfs.find_direct_trips_by_name(
                origin,
                destination,
                max_results=5,
            )
        except Exception:
            # GTFS should normally not fail here, but the routing layer
            # should remain resilient during the prototype.
            trips = []

        if trips:
            routes = [
                self._trip_to_candidate_route(trip)
                for trip in trips
            ]

            routes = self._deduplicate_routes(routes)

            if routes:
                return routes

        # --------------------------------------------------------------
        # 2. No direct GTFS route.
        #
        # Return deterministic fallback candidates.
        #
        # This keeps:
        #
        #   /api/recommend
        #   /api/routes
        #
        # usable for demo locations and arbitrary stop names.
        # --------------------------------------------------------------

        return self._fallback_candidate_routes(
            origin,
            destination,
        )

    # ------------------------------------------------------------------
    # Route lookup
    # ------------------------------------------------------------------

    def get_route_by_id(
        self,
        origin: str,
        destination: str,
        route_id: str,
    ) -> CandidateRoute:
        """
        Return one candidate route by route_id.

        The method first obtains candidates using the normal routing
        pipeline, then searches for the requested route ID.
        """

        candidates = self.get_candidate_routes(
            origin,
            destination,
        )

        for route in candidates:
            if route.route_id == route_id:
                return route

        raise RouteNotFoundError(
            f"Route '{route_id}' not found from "
            f"'{origin}' to '{destination}'."
        )

    # ------------------------------------------------------------------
    # GTFS → application adapter
    # ------------------------------------------------------------------

    @staticmethod
    def _trip_to_candidate_route(
        trip: GTFSDirectTrip,
    ) -> CandidateRoute:
        """
        Convert one GTFSDirectTrip into the application's
        CandidateRoute structure.

        GTFS-specific objects never escape RoutingService.
        """

        line = (
            trip.route_short_name
            or trip.route_long_name
            or trip.route_id
        )

        route_name = (
            f"{trip.origin_stop_name} → "
            f"{trip.destination_stop_name}"
        )

        travel_minutes = max(
            1,
            int(trip.travel_minutes),
        )

        leg = MockLeg(
            mode="BUS",
            line=line,
            travel_minutes=travel_minutes,
        )

        return CandidateRoute(
            route_id=str(trip.route_id),
            route_name=route_name,
            legs=[leg],
            base_travel_minutes=travel_minutes,
            base_waiting_minutes=0,
            transfers=0,
        )

    # ------------------------------------------------------------------
    # Fallback routing
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_candidate_routes(
        origin: str,
        destination: str,
    ) -> list[CandidateRoute]:
        """
        Generate deterministic fallback routes.

        These routes are NOT claiming to be real GTFS routes.

        They exist so the prototype can continue to demonstrate:

            origin
                ↓
            routing
                ↓
            prediction
                ↓
            scoring
                ↓
            recommendation

        even when the GTFS feed has no direct trip for the requested
        pair.

        The route contract is intentionally identical to the real
        GTFS-backed routes.
        """

        # Create a stable deterministic value from the stop names.
        seed = sum(
            ord(character)
            for character in f"{origin}|{destination}"
        )

        # Keep the values within sensible demo ranges.
        route_a_minutes = 25 + (seed % 11)
        route_b_minutes = route_a_minutes + 6
        route_c_minutes = route_a_minutes + 12

        return [
            CandidateRoute(
                route_id="fallback-direct",
                route_name=(
                    f"{origin} → {destination}"
                ),
                legs=[
                    MockLeg(
                        mode="BUS",
                        line="DTC",
                        travel_minutes=route_a_minutes,
                    )
                ],
                base_travel_minutes=route_a_minutes,
                base_waiting_minutes=5,
                transfers=0,
            ),
            CandidateRoute(
                route_id="fallback-metro",
                route_name=(
                    f"{origin} → {destination} via Metro"
                ),
                legs=[
                    MockLeg(
                        mode="METRO",
                        line="Delhi Metro",
                        travel_minutes=route_b_minutes,
                    )
                ],
                base_travel_minutes=route_b_minutes,
                base_waiting_minutes=4,
                transfers=1,
            ),
            CandidateRoute(
                route_id="fallback-mixed",
                route_name=(
                    f"{origin} → {destination} via Bus + Metro"
                ),
                legs=[
                    MockLeg(
                        mode="BUS",
                        line="DTC",
                        travel_minutes=route_c_minutes // 2,
                    ),
                    MockLeg(
                        mode="METRO",
                        line="Delhi Metro",
                        travel_minutes=route_c_minutes
                        - (route_c_minutes // 2),
                    ),
                ],
                base_travel_minutes=route_c_minutes,
                base_waiting_minutes=7,
                transfers=1,
            ),
        ]

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate_routes(
        routes: list[CandidateRoute],
    ) -> list[CandidateRoute]:
        """
        Remove duplicate route IDs while preserving the best
        travel-time candidate.
        """

        best: dict[str, CandidateRoute] = {}

        for route in routes:
            current = best.get(route.route_id)

            if (
                current is None
                or route.base_travel_minutes
                < current.base_travel_minutes
            ):
                best[route.route_id] = route

        result = list(best.values())

        result.sort(
            key=lambda route: (
                route.base_travel_minutes,
                route.base_waiting_minutes,
                route.transfers,
                route.route_id,
            )
        )

        return result

    # ------------------------------------------------------------------
    # Stop-name support
    # ------------------------------------------------------------------

    def _all_stop_names(self) -> list[str]:
        """
        Return all known GTFS stop names.

        GTFSService owns the actual GTFS storage, so RoutingService
        accesses it through the public helper.
        """

        return self.gtfs.all_stop_names()
