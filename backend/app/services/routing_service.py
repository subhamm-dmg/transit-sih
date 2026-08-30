"""
RoutingService — generates candidate journeys from the Delhi DTC GTFS feed.

GTFSService owns data loading and direct-trip discovery.
RoutingService converts GTFS results into CandidateRoute objects.

The public get_candidate_routes() contract is intentionally stable so
RecommendationService and the API layer do not need to change.
"""

from dataclasses import dataclass

from app.services.gtfs_service import GTFSService


@dataclass(frozen=True)
class MockLeg:
    """One leg of a candidate journey."""

    mode: str
    line: str
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


class RouteNotFoundError(Exception):
    """Raised when no candidate route can be generated."""


class RoutingService:
    """Generates candidate journeys using Delhi DTC GTFS data."""

    def __init__(
        self,
        gtfs_service: GTFSService | None = None,
    ) -> None:
        self.gtfs_service = gtfs_service or GTFSService()

    def known_stops(self) -> set[str]:
        """Return all known Delhi DTC stop names."""
        return {
            stop.stop_name.lower()
            for stop in self.gtfs_service._stops.values()
        }

    def get_candidate_routes(
        self,
        origin: str,
        destination: str,
    ) -> list[CandidateRoute]:
        """
        Return direct DTC candidate routes between two stops.

        GTFSService discovers scheduled direct trips. This method converts
        those trips into the CandidateRoute contract used by the rest of
        the backend.

        Routes are deduplicated by user-facing route name so multiple
        GTFS route IDs representing the same service are not displayed
        as duplicate alternatives.
        """

        if origin.strip().lower() == destination.strip().lower():
            raise RouteNotFoundError(
                "Origin and destination must be different stops"
            )

        trips = self.gtfs_service.find_direct_trips_by_name(
            origin,
            destination,
            max_results=10,
        )

        if not trips:
            raise RouteNotFoundError(
                f"No direct DTC routes found from '{origin}' to '{destination}'"
            )

        candidates: list[CandidateRoute] = []

        # Avoid showing duplicate user-facing route names.
        seen_route_names: set[str] = set()

        for trip in trips:
            route_name = trip.route_short_name.strip()

            if not route_name:
                route_name = trip.route_long_name.strip()

            if not route_name:
                route_name = f"DTC Route {trip.route_id}"

            normalized_name = route_name.casefold()

            if normalized_name in seen_route_names:
                continue

            seen_route_names.add(normalized_name)

            candidates.append(
                CandidateRoute(
                    route_id=trip.route_id,
                    route_name=route_name,
                    legs=[
                        MockLeg(
                            mode="BUS",
                            line=route_name,
                            travel_minutes=trip.travel_minutes,
                        )
                    ],
                    base_travel_minutes=trip.travel_minutes,
                    base_waiting_minutes=0,
                    transfers=0,
                )
            )

        return candidates

    def get_route_by_id(
        self,
        origin: str,
        destination: str,
        route_id: str,
    ) -> CandidateRoute | None:
        """Return one GTFS-backed candidate route by route ID."""

        routes = self.get_candidate_routes(origin, destination)

        for route in routes:
            if route.route_id == route_id:
                return route

        return None


__all__ = [
    "CandidateRoute",
    "MockLeg",
    "RouteNotFoundError",
    "RoutingService",
]
