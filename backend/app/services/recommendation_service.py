"""
RecommendationService — orchestrates RoutingService + PredictionService +
scoring to build the final ranked list of RouteOption objects.

This is the single place that composes candidate routes with predictions
and a score, so /api/routes and /api/recommend both build results the
same way instead of duplicating logic in the route handlers.
"""

from __future__ import annotations

from app.models.schemas import CrowdLevel, RecommendationMetadata, RouteOption
from app.services import scoring_service
from app.services.prediction_service import PREDICTION_MODE, PredictionService
from app.services.routing_service import RouteNotFoundError, RoutingService


class RecommendationService:
    def __init__(
        self,
        routing_service: RoutingService | None = None,
        prediction_service: PredictionService | None = None,
    ) -> None:
        self.routing_service = routing_service or RoutingService()
        self.prediction_service = prediction_service or PredictionService()

    def get_ranked_routes(
        self, origin: str, destination: str, departure_time: str
    ) -> tuple[list[RouteOption], RecommendationMetadata]:
        """
        Return (routes, metadata), routes sorted best-first (lowest score).

        Raises RouteNotFoundError if no candidate routes exist for the pair.
        """
        candidates = self.routing_service.get_candidate_routes(origin, destination)
        if not candidates:
            raise RouteNotFoundError(f"No routes found from '{origin}' to '{destination}'")

        options: list[RouteOption] = []
        for candidate in candidates:
            eta = self.prediction_service.predict_eta(
                candidate.base_travel_minutes, candidate.route_id, departure_time
            )
            delay = self.prediction_service.predict_delay(candidate.route_id, departure_time)
            crowding = self.prediction_service.predict_crowding(
                candidate.route_id, departure_time, candidate.transfers
            )
            reliability = scoring_service.compute_reliability(delay, candidate.transfers)
            score = scoring_service.score_route(
                eta_minutes=eta,
                waiting_minutes=candidate.base_waiting_minutes,
                delay_minutes=delay,
                crowd_score=crowding.crowd_score,
                transfers=candidate.transfers,
                reliability=reliability,
            )

            options.append(
                RouteOption(
                    route_id=candidate.route_id,
                    route_name=candidate.route_name,
                    eta_minutes=eta,
                    waiting_minutes=candidate.base_waiting_minutes,
                    delay_minutes=delay,
                    crowd_level=CrowdLevel(crowding.crowd_level.value),
                    crowd_score=crowding.crowd_score,
                    reliability=reliability,
                    transfers=candidate.transfers,
                    reason="",  # filled in below once ranking is known
                    score=score,
                )
            )

        options.sort(key=lambda opt: opt.score if opt.score is not None else float("inf"))

        for index, option in enumerate(options):
            option.reason = scoring_service.build_reason(
                is_recommended=(index == 0),
                eta_minutes=option.eta_minutes,
                crowd_level=option.crowd_level.value,
                delay_minutes=option.delay_minutes,
            )

        metadata = RecommendationMetadata(
            prediction_mode=PREDICTION_MODE,
            data_source="mock",
            confidence=0.75,
        )
        return options, metadata


__all__ = ["RecommendationService", "RouteNotFoundError"]
