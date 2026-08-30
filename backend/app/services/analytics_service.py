"""
Government-side transport analytics.

This module is deliberately separate from prediction/scoring/recommendation.

Important data semantics:
- GTFS schedule frequency is a SERVICE-PRESSURE / DEMAND PROXY.
- No actual passenger counts are invented.
- No real-time delay values are invented.
- No actual crowding values are invented.
- DTC and Metro are kept as separate datasets.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.gtfs_service import GTFSService


class AnalyticsService:
    """Cached aggregate analytics over local GTFS feeds."""

    def __init__(
        self,
        dtc_service: GTFSService | None = None,
        metro_service: GTFSService | None = None,
    ) -> None:
        self._dtc = dtc_service or GTFSService()

        if metro_service is not None:
            self._metro = metro_service
        else:
            metro_path = (
                Path(__file__).resolve().parents[3]
                / "data"
                / "processed"
                / "gtfs_metro"
            )
            try:
                self._metro = GTFSService(metro_path)
            except Exception:
                self._metro = None

        self._cache: dict[str, dict[str, Any]] = {}

        self._dtc_data = self._build_dataset("DTC", self._dtc)

        self._metro_data = (
            self._build_dataset("METRO", self._metro)
            if self._metro is not None
            else self._unavailable_dataset("METRO")
        )

    # ------------------------------------------------------------------
    # Dataset preparation
    # ------------------------------------------------------------------

    @staticmethod
    def _unavailable_dataset(name: str) -> dict[str, Any]:
        return {
            "dataset": name,
            "available": False,
            "stop_count": 0,
            "route_count": 0,
            "trip_count": 0,
            "stop_time_count": 0,
            "hourly_departures": Counter(),
            "stop_departures": Counter(),
            "stop_routes": defaultdict(set),
            "route_departures": Counter(),
            "route_names": {},
        }

    @staticmethod
    def _parse_hour(value: str) -> int | None:
        try:
            parts = value.split(":")
            if len(parts) != 3:
                return None

            hour = int(parts[0])

            # GTFS permits >24 hour service times.
            return hour % 24
        except (TypeError, ValueError):
            return None

    def _build_dataset(
        self,
        name: str,
        service: GTFSService,
    ) -> dict[str, Any]:
        """
        Build all aggregates in one pass over stop_times.

        The resulting dictionary is cached and reused for every API request.
        """

        hourly_departures: Counter[int] = Counter()
        stop_departures: Counter[str] = Counter()
        stop_routes: defaultdict[str, set[str]] = defaultdict(set)
        route_departures: Counter[str] = Counter()
        route_names: dict[str, str] = {}

        for (
            stop_id,
            trip_id,
            _sequence,
            _arrival,
            departure,
        ) in service.iter_stop_time_records():

            if not departure:
                continue

            hour = self._parse_hour(departure)
            if hour is not None:
                hourly_departures[hour] += 1

            stop_departures[stop_id] += 1

            trip = service.get_trip(trip_id)
            if trip is None:
                continue

            route_id = trip.route_id
            route_departures[route_id] += 1
            stop_routes[stop_id].add(route_id)

            route = service.get_route(route_id)
            if route is not None:
                route_name = (
                    route.route_short_name.strip()
                    or route.route_long_name.strip()
                    or route.route_id
                )
                route_names[route_id] = route_name

        return {
            "dataset": name,
            "available": True,
            "stop_count": service.stop_count(),
            "route_count": service.route_count(),
            "trip_count": service.trip_count(),
            "stop_time_count": service.stop_time_count(),
            "hourly_departures": hourly_departures,
            "stop_departures": stop_departures,
            "stop_routes": stop_routes,
            "route_departures": route_departures,
            "route_names": route_names,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hour_label(hour: int) -> str:
        suffix = "AM" if hour < 12 else "PM"
        display = hour % 12 or 12
        return f"{display:02d}:00 {suffix}"

    @staticmethod
    def _dataset_summary(data: dict[str, Any]) -> dict[str, Any]:
        return {
            "dataset": data["dataset"],
            "available": data["available"],
            "stop_count": data["stop_count"],
            "route_count": data["route_count"],
            "trip_count": data["trip_count"],
            "stop_time_count": data["stop_time_count"],
        }

    @staticmethod
    def _top_stops(
        data: dict[str, Any],
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        rows = []

        for stop_id, departures in data["stop_departures"].items():
            rows.append(
                {
                    "stop_id": stop_id,
                    "scheduled_departures": departures,
                    "route_count": len(data["stop_routes"].get(stop_id, set())),
                }
            )

        rows.sort(
            key=lambda x: (
                -x["scheduled_departures"],
                -x["route_count"],
                x["stop_id"],
            )
        )

        return rows[:limit]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        dtc = self._dtc_data
        hourly = dtc["hourly_departures"]

        peak_hour = max(
            hourly,
            key=lambda h: (hourly[h], -h),
            default=None,
        )

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dtc": self._dataset_summary(dtc),
            "metro": self._dataset_summary(self._metro_data),
            "scheduled_service": {
                "total_scheduled_departures": sum(hourly.values()),
                "peak_hour": (
                    self._hour_label(peak_hour)
                    if peak_hour is not None
                    else None
                ),
                "peak_hour_departures": (
                    hourly[peak_hour] if peak_hour is not None else 0
                ),
            },
            "data_limitations": [
                "Scheduled departures are a service-frequency proxy, not observed passenger demand.",
                "No real-time vehicle feed is connected.",
                "No observed ridership feed is connected.",
                "No observed crowding feed is connected.",
            ],
        }

    def demand(self) -> dict[str, Any]:
        datasets = []

        for data in (self._dtc_data, self._metro_data):
            hourly = [
                {
                    "hour": hour,
                    "label": self._hour_label(hour),
                    "scheduled_departures": data["hourly_departures"].get(
                        hour, 0
                    ),
                }
                for hour in range(24)
            ]

            top_routes = []
            for route_id, count in data["route_departures"].items():
                top_routes.append(
                    {
                        "route_id": route_id,
                        "route_name": data["route_names"].get(
                            route_id,
                            route_id,
                        ),
                        "scheduled_departures": count,
                    }
                )

            top_routes.sort(
                key=lambda x: (
                    -x["scheduled_departures"],
                    x["route_id"],
                )
            )

            datasets.append(
                {
                    "dataset": data["dataset"],
                    "available": data["available"],
                    "metric": "scheduled_service_pressure",
                    "metric_definition": (
                        "Number of scheduled stop departures in the GTFS feed. "
                        "Use as a service-frequency proxy, not as actual passenger demand."
                    ),
                    "hourly": hourly,
                    "top_stops": self._top_stops(data),
                    "top_routes": top_routes[:10],
                }
            )

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "datasets": datasets,
        }

    def delays(self) -> dict[str, Any]:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "delay_data_available": False,
            "delay_source": "no_realtime_vehicle_feed_connected",
            "scheduled_baseline": {
                "description": (
                    "GTFS provides scheduled arrival/departure times only. "
                    "They cannot be converted into actual delay measurements."
                ),
                "available": True,
            },
            "datasets": [
                {
                    "dataset": "DTC",
                    "available": True,
                    "observed_delay_minutes": None,
                },
                {
                    "dataset": "METRO",
                    "available": self._metro_data["available"],
                    "observed_delay_minutes": None,
                },
            ],
            "limitations": [
                "No GTFS-Realtime vehicle position/trip-update feed is connected.",
                "Actual delay requires observed or real-time arrival/departure data.",
            ],
        }

    def crowding(self) -> dict[str, Any]:
        datasets = []

        for data in (self._dtc_data, self._metro_data):
            pressure = self._top_stops(data)

            datasets.append(
                {
                    "dataset": data["dataset"],
                    "available": data["available"],
                    "crowding_data_available": False,
                    "crowding_source": "no_ridership_or_crowding_feed_connected",
                    "scheduled_service_pressure": pressure,
                }
            )

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "datasets": datasets,
            "limitations": [
                "No passenger-count or occupancy feed is connected.",
                "Scheduled service pressure must not be interpreted as actual crowding.",
            ],
        }

    def bottlenecks(self) -> dict[str, Any]:
        cached = self._cache.get("bottlenecks")
        if cached is not None:
            return cached

        datasets = []

        for data in (self._dtc_data, self._metro_data):
            if not data["available"]:
                datasets.append(
                    {
                        "dataset": data["dataset"],
                        "available": False,
                        "metric": "scheduled_service_bottleneck_proxy",
                        "bottlenecks": [],
                    }
                )
                continue

            max_departures = max(
                data["stop_departures"].values(),
                default=1,
            )
            max_routes = max(
                (
                    len(routes)
                    for routes in data["stop_routes"].values()
                ),
                default=1,
            )

            rows = []

            for stop_id, departures in data["stop_departures"].items():
                route_count = len(
                    data["stop_routes"].get(stop_id, set())
                )

                departure_component = departures / max_departures
                route_component = route_count / max_routes

                score = round(
                    100
                    * (
                        0.70 * departure_component
                        + 0.30 * route_component
                    ),
                    2,
                )

                rows.append(
                    {
                        "stop_id": stop_id,
                        "scheduled_departures": departures,
                        "route_count": route_count,
                        "score": score,
                        "reason": (
                            "High scheduled service pressure based on "
                            "departure frequency and route diversity."
                        ),
                    }
                )

            rows.sort(
                key=lambda x: (
                    -x["score"],
                    -x["scheduled_departures"],
                    x["stop_id"],
                )
            )

            datasets.append(
                {
                    "dataset": data["dataset"],
                    "available": True,
                    "metric": "scheduled_service_bottleneck_proxy",
                    "bottlenecks": rows[:10],
                }
            )

        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "datasets": datasets,
            "interpretation": (
                "These are schedule-based service-pressure bottlenecks, "
                "not measured passenger congestion."
            ),
        }

        self._cache["bottlenecks"] = result
        return result
