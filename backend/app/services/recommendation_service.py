"""
RecommendationService — orchestrates RoutingService + PredictionService +
ScoringService to build the final ranked list of RouteOption objects.

This is the single place that composes candidate routes with predictions
and a score, so /api/routes and /api/recommend both build results the
same way instead of duplicating logic in the route handlers.

PredictionService does NOT decide which route wins - ScoringService still
owns ranking. This module just wires the two together and supplies
optional traffic/weather context to the prediction engine, degrading
gracefully (falling back to pure heuristics) if either is unavailable.
"""

from datetime import datetime

from app.models.schemas import RecommendationMetadata, RouteOption
from app.services import scoring_service
from app.services.prediction_service import PredictionService, RouteInfo
from app.services.routing_service import RouteNotFoundError, RoutingService
from app.services.traffic_service import TrafficService
from app.services.weather_service import WeatherService


class RecommendationService:
    def __init__(
        self,
        routing_service: RoutingService | None = None,
        prediction_service: PredictionService | None = None,
        traffic_service: TrafficService | None = None,
        weather_service: WeatherService | None = None,
    ) -> None:
        self.routing_service = routing_service or RoutingService()
        self.prediction_service = prediction_service or PredictionService()
        # Optional data sources. Never let a failure here break the whole
        # request - see _get_traffic_info / _get_weather_info below.
        self.traffic_service = traffic_service or TrafficService()
        self.weather_service = weather_service or WeatherService()

    def get_ranked_routes(
        self, origin: str, destination: str, departure_time: str
    ) -> tuple[list[RouteOption], RecommendationMetadata]:
        """
        Return (routes, metadata), routes sorted best-first (lowest score).

        Raises RouteNotFoundError if no candidate routes exist for the pair.
        """
        candidates = self.routing_service.get_candidate_routes(
            origin, destination, departure_time
        )
        if not candidates:
            raise RouteNotFoundError(f"No routes found from '{origin}' to '{destination}'")

        is_weekend = datetime.now().weekday() >= 5  # Sat=5, Sun=6
        traffic_info = self._get_traffic_info(destination, departure_time)
        weather_info = self._get_weather_info(destination, departure_time)

        options: list[RouteOption] = []
        prediction_modes: set[str] = set()
        data_sources: set[str] = set()
        confidences: list[float] = []

        for candidate in candidates:
            route_info = RouteInfo.from_candidate(candidate)
            prediction = self.prediction_service.predict(
                route_info,
                departure_time=departure_time,
                is_weekend=is_weekend,
                traffic_info=traffic_info,
                weather_info=weather_info,
            )

            reliability = scoring_service.compute_reliability(
                prediction.delay_minutes, candidate.transfers
            )
            score = scoring_service.score_route(
                eta_minutes=prediction.eta_minutes,
                waiting_minutes=candidate.base_waiting_minutes,
                delay_minutes=prediction.delay_minutes,
                crowd_score=prediction.crowd_score,
                transfers=candidate.transfers,
                reliability=reliability,
            )

            options.append(
                RouteOption(
                    route_id=candidate.route_id,
                    route_name=candidate.route_name,
                    eta_minutes=prediction.eta_minutes,
                    waiting_minutes=candidate.base_waiting_minutes,
                    delay_minutes=prediction.delay_minutes,
                    crowd_level=prediction.crowd_level.value,
                    crowd_score=prediction.crowd_score,
                    reliability=reliability,
                    transfers=candidate.transfers,
                    reason="",  # filled in below once ranking is known
                    score=score,
                    eta_confidence=prediction.eta_confidence,
                    delay_confidence=prediction.delay_confidence,
                    crowd_confidence=prediction.crowd_confidence,
                )
            )
            prediction_modes.add(prediction.prediction_mode)
            data_sources.add(prediction.data_source)
            confidences.append(
                (prediction.eta_confidence + prediction.delay_confidence + prediction.crowd_confidence) / 3
            )

        options.sort(key=lambda opt: opt.score if opt.score is not None else float("inf"))

        for index, option in enumerate(options):
            option.reason = scoring_service.build_reason(
                is_recommended=(index == 0),
                eta_minutes=option.eta_minutes,
                crowd_level=option.crowd_level.value,
                delay_minutes=option.delay_minutes,
            )

        overall_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.5
        metadata = RecommendationMetadata(
            prediction_mode="+".join(sorted(prediction_modes)) or "heuristic",
            data_source="+".join(sorted(data_sources)) or "heuristic",
            confidence=overall_confidence,
        )
        return options, metadata

    # -- optional data sources: never let these break a request ------------

    def _get_traffic_info(self, area: str, departure_time: str):
        try:
            return self.traffic_service.get_traffic_level(area, departure_time)
        except Exception:
            # Traffic data unavailable -> PredictionService falls back to
            # its own peak-hour heuristic. Never fail the request for this.
            return None

    def _get_weather_info(self, area: str, departure_time: str):
        try:
            return self.weather_service.get_weather(area, departure_time)
        except Exception:
            # Same graceful-degradation contract as traffic above.
            return None


__all__ = ["RecommendationService", "RouteNotFoundError"]
