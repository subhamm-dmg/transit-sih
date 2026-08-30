"""
GTFSService — lightweight reader for the Delhi/DTC GTFS static feed.

Responsibilities:
    - Load stops.txt
    - Load routes.txt
    - Load trips.txt
    - Load stop_times.txt
    - Provide stop-name lookup
    - Provide direct-trip lookup between two stops
    - Provide route/trip information to RoutingService

This service deliberately does NOT:
    - rank routes
    - predict ETA
    - predict crowding
    - call Google Routes
    - call external APIs

RoutingService is responsible for converting GTFS results into the
application's CandidateRoute contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from zipfile import ZipFile
import csv
import io


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GTFSStop:
    stop_id: str
    stop_name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class GTFSRoute:
    route_id: str
    route_short_name: str
    route_long_name: str
    route_type: int


@dataclass(frozen=True)
class GTFSTrip:
    trip_id: str
    route_id: str
    service_id: str


@dataclass(frozen=True)
class GTFSDirectTrip:
    """
    One scheduled GTFS trip that serves origin and destination directly.
    """

    trip_id: str
    route_id: str
    route_short_name: str
    route_long_name: str
    origin_stop_id: str
    origin_stop_name: str
    destination_stop_id: str
    destination_stop_name: str
    departure_time: str
    arrival_time: str
    travel_minutes: int


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class GTFSService:
    """
    Reads the DTC GTFS ZIP file into memory.

    The default path is:

        data/raw/dtc_gtfs.zip

    from the repository root.
    """

    def __init__(self, feed_path: str | Path | None = None) -> None:
        if feed_path is None:
            feed_path = (
                Path(__file__).resolve().parents[3]
                / "data"
                / "processed"
                / "dtc_gtfs"
            )

        self.feed_path = Path(feed_path)

        if not self.feed_path.exists():
            raise FileNotFoundError(
                f"GTFS feed not found: {self.feed_path}"
            )

        self._stops: dict[str, GTFSStop] = {}
        self._routes: dict[str, GTFSRoute] = {}
        self._trips: dict[str, GTFSTrip] = {}

        # stop_id -> ordered list of (trip_id, stop_sequence, arrival, departure)
        self._stop_times: dict[
            str,
            list[tuple[str, int, str, str]],
        ] = {}

        # trip_id -> route_id
        self._trip_route: dict[str, str] = {}

        # trip_id -> list of stop records in stop_sequence order
        self._trip_stop_times: dict[
            str,
            list[tuple[str, int, str, str]],
        ] = {}

        self._load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self.feed_path.is_dir():
            self._load_stops(self.feed_path)
            self._load_routes(self.feed_path)
            self._load_trips(self.feed_path)
            self._load_stop_times(self.feed_path)
            return

        if self.feed_path.is_file() and self.feed_path.suffix.lower() == ".zip":
            with ZipFile(self.feed_path, "r") as archive:
                self._load_stops(archive)
                self._load_routes(archive)
                self._load_trips(archive)
                self._load_stop_times(archive)
            return

        raise FileNotFoundError(
            f"GTFS feed must be a directory or ZIP file: {self.feed_path}"
        )

    @staticmethod
    def _read_csv(
        source: Path | ZipFile,
        filename: str,
    ) -> Iterator[dict[str, str]]:
        if isinstance(source, ZipFile):
            raw = source.open(filename, "r")
            close_raw = True
        else:
            raw = source.joinpath(filename).open("rb")
            close_raw = True

        try:
            text = io.TextIOWrapper(
                raw,
                encoding="utf-8-sig",
                newline="",
            )

            reader = csv.DictReader(text)

            for row in reader:
                yield {
                    str(key).strip(): (value or "").strip()
                    for key, value in row.items()
                }
        finally:
            if close_raw:
                raw.close()

    def _load_stops(self, source: Path | ZipFile) -> None:
        for row in self._read_csv(source, "stops.txt"):
            try:
                stop = GTFSStop(
                    stop_id=row["stop_id"],
                    stop_name=row["stop_name"],
                    latitude=float(row["stop_lat"]),
                    longitude=float(row["stop_lon"]),
                )
            except (KeyError, TypeError, ValueError):
                continue

            self._stops[stop.stop_id] = stop

    def _load_routes(self, source: Path | ZipFile) -> None:
        for row in self._read_csv(source, "routes.txt"):
            try:
                route = GTFSRoute(
                    route_id=row["route_id"],
                    route_short_name=row.get("route_short_name", ""),
                    route_long_name=row.get("route_long_name", ""),
                    route_type=int(row.get("route_type", "3") or "3"),
                )
            except (KeyError, TypeError, ValueError):
                continue

            self._routes[route.route_id] = route

    def _load_trips(self, source: Path | ZipFile) -> None:
        for row in self._read_csv(source, "trips.txt"):
            try:
                trip = GTFSTrip(
                    trip_id=row["trip_id"],
                    route_id=row["route_id"],
                    service_id=row.get("service_id", ""),
                )
            except KeyError:
                continue

            self._trips[trip.trip_id] = trip
            self._trip_route[trip.trip_id] = trip.route_id

    def _load_stop_times(self, source: Path | ZipFile) -> None:
        for row in self._read_csv(source, "stop_times.txt"):
            try:
                trip_id = row["trip_id"]
                stop_id = row["stop_id"]
                sequence = int(row["stop_sequence"])
                arrival = row.get("arrival_time", "")
                departure = row.get("departure_time", "")
            except (KeyError, TypeError, ValueError):
                continue

            record = (
                trip_id,
                sequence,
                arrival,
                departure,
            )

            self._stop_times.setdefault(
                stop_id,
                [],
            ).append(record)

            self._trip_stop_times.setdefault(
                trip_id,
                [],
            ).append(
                (
                    stop_id,
                    sequence,
                    arrival,
                    departure,
                )
            )

        # Make trip stop sequences deterministic.
        for records in self._trip_stop_times.values():
            records.sort(key=lambda item: item[1])

        for records in self._stop_times.values():
            records.sort(key=lambda item: (item[0], item[1]))

    # ------------------------------------------------------------------
    # Basic information
    # ------------------------------------------------------------------

    def stop_count(self) -> int:
        return len(self._stops)

    def route_count(self) -> int:
        return len(self._routes)

    def trip_count(self) -> int:
        return len(self._trips)

    def stop_time_count(self) -> int:
        return sum(
            len(records)
            for records in self._stop_times.values()
        )

    # ------------------------------------------------------------------
    # Stop lookup
    # ------------------------------------------------------------------

    def get_stop(self, stop_id: str) -> GTFSStop | None:
        return self._stops.get(stop_id)

    def find_stops(
        self,
        name: str,
        *,
        max_results: int = 10,
    ) -> list[GTFSStop]:
        """
        Case-insensitive substring search over stop names.
        """

        query = name.strip().lower()

        if not query:
            return []

        exact: list[GTFSStop] = []
        partial: list[GTFSStop] = []

        for stop in self._stops.values():
            stop_name = stop.stop_name.lower()

            if stop_name == query:
                exact.append(stop)
            elif query in stop_name:
                partial.append(stop)

        exact.sort(key=lambda stop: stop.stop_name.lower())
        partial.sort(key=lambda stop: stop.stop_name.lower())

        return (exact + partial)[:max_results]

    def find_stop(
        self,
        name: str,
    ) -> GTFSStop | None:
        results = self.find_stops(name, max_results=1)
        return results[0] if results else None

    # ------------------------------------------------------------------
    # Route lookup
    # ------------------------------------------------------------------

    def get_route(
        self,
        route_id: str,
    ) -> GTFSRoute | None:
        return self._routes.get(route_id)

    # ------------------------------------------------------------------
    # Direct-trip lookup
    # ------------------------------------------------------------------

    @staticmethod
    def _time_to_seconds(value: str) -> int:
        """
        GTFS allows times beyond 24:00:00.

        Example:
            25:15:00 -> next day 01:15

        Keeping the raw GTFS hour makes chronological comparisons work.
        """

        try:
            parts = value.split(":")

            if len(parts) != 3:
                return 0

            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(float(parts[2]))

            return (
                hours * 3600
                + minutes * 60
                + seconds
            )

        except (ValueError, TypeError):
            return 0

    @classmethod
    def _travel_minutes(
        cls,
        departure_time: str,
        arrival_time: str,
    ) -> int:
        departure = cls._time_to_seconds(departure_time)
        arrival = cls._time_to_seconds(arrival_time)

        if arrival < departure:
            arrival += 24 * 60 * 60

        seconds = max(0, arrival - departure)

        return max(
            1,
            round(seconds / 60),
        )

    def find_direct_trips(
        self,
        origin_stop: str,
        destination_stop: str,
        *,
        max_results: int = 5,
    ) -> list[GTFSDirectTrip]:
        """
        Find trips that visit origin before destination.

        Important:
            This returns at most one result per route.

        We deliberately do NOT return 20 identical trips from the same
        route. RoutingService needs candidate route alternatives, not
        every scheduled departure.
        """

        if (
            origin_stop not in self._stops
            or destination_stop not in self._stops
        ):
            return []

        origin_records = self._stop_times.get(
            origin_stop,
            [],
        )

        destination_records = self._stop_times.get(
            destination_stop,
            [],
        )

        if not origin_records or not destination_records:
            return []

        # Build:
        # trip_id -> (sequence, arrival, departure)
        destination_by_trip: dict[
            str,
            tuple[int, str, str],
        ] = {}

        for (
            trip_id,
            sequence,
            arrival,
            departure,
        ) in destination_records:
            destination_by_trip[trip_id] = (
                sequence,
                arrival,
                departure,
            )

        results: list[GTFSDirectTrip] = []

        # One candidate per route.
        best_by_route: dict[
            str,
            GTFSDirectTrip,
        ] = {}

        for (
            trip_id,
            origin_sequence,
            _origin_arrival,
            origin_departure,
        ) in origin_records:

            destination_data = destination_by_trip.get(
                trip_id
            )

            if destination_data is None:
                continue

            (
                destination_sequence,
                destination_arrival,
                _destination_departure,
            ) = destination_data

            # Destination must occur AFTER origin.
            if destination_sequence <= origin_sequence:
                continue

            trip = self._trips.get(trip_id)

            if trip is None:
                continue

            route = self._routes.get(trip.route_id)

            if route is None:
                continue

            travel_minutes = self._travel_minutes(
                origin_departure,
                destination_arrival,
            )

            candidate = GTFSDirectTrip(
                trip_id=trip_id,
                route_id=route.route_id,
                route_short_name=route.route_short_name,
                route_long_name=route.route_long_name,
                origin_stop_id=origin_stop,
                origin_stop_name=self._stops[
                    origin_stop
                ].stop_name,
                destination_stop_id=destination_stop,
                destination_stop_name=self._stops[
                    destination_stop
                ].stop_name,
                departure_time=origin_departure,
                arrival_time=destination_arrival,
                travel_minutes=travel_minutes,
            )

            current = best_by_route.get(
                route.route_id
            )

            # Pick the shortest scheduled journey for
            # this route. This keeps results compact.
            if (
                current is None
                or candidate.travel_minutes
                < current.travel_minutes
            ):
                best_by_route[route.route_id] = candidate

        results = list(best_by_route.values())

        results.sort(
            key=lambda item: (
                item.travel_minutes,
                item.route_short_name,
                item.route_id,
            )
        )

        return results[:max_results]

    def find_direct_trips_by_name(
        self,
        origin_name: str,
        destination_name: str,
        *,
        max_results: int = 5,
    ) -> list[GTFSDirectTrip]:
        """
        Convenience wrapper for RoutingService.

        Searches stop names first, then performs the direct-trip lookup.
        """

        origin_stops = self.find_stops(
            origin_name,
            max_results=5,
        )

        destination_stops = self.find_stops(
            destination_name,
            max_results=5,
        )

        if not origin_stops or not destination_stops:
            return []

        results: list[GTFSDirectTrip] = []

        seen_routes: set[str] = set()

        for origin in origin_stops:
            for destination in destination_stops:
                if origin.stop_id == destination.stop_id:
                    continue

                trips = self.find_direct_trips(
                    origin.stop_id,
                    destination.stop_id,
                    max_results=max_results,
                )

                for trip in trips:
                    if trip.route_id in seen_routes:
                        continue

                    seen_routes.add(trip.route_id)
                    results.append(trip)

        results.sort(
            key=lambda item: (
                item.travel_minutes,
                item.route_short_name,
                item.route_id,
            )
        )

        return results[:max_results]
