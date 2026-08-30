"""
backend/app/services/recommendation_service.py — Orchestrates Routing, ML Prediction, and Scoring.

Receives commuter query (from, to, departure_time), finds candidate routes,
runs ML models for ETA / delay / crowding, computes multi-objective ranking, and formats response.
"""

from __future__ import annotations

from typing import Optional
from app.models.schemas import (
    CrowdLevel,
    JourneyLegSchema,
    RecommendationMetadata,
    RouteOption,
)
from app.services import scoring_service
from app.services.prediction_service import PREDICTION_MODE, PredictionService
from app.services.routing_service import CandidateRoute, RouteNotFoundError, RoutingService


class RecommendationService:
    def __init__(
        self,
        routing_service: Optional[RoutingService] = None,
        prediction_service: Optional[PredictionService] = None,
    ):
        self.routing_service = routing_service or RoutingService()
        self.prediction_service = prediction_service or PredictionService()

    def get_ranked_routes(
        self, origin: str, destination: str, departure_time: str
    ) -> tuple[list[RouteOption], RecommendationMetadata]:
        """
        Builds and ranks candidate routes based on ML predictions.
        """
        candidates = self.routing_service.get_candidate_routes(origin, destination)
        if not candidates:
            raise RouteNotFoundError(f"No routes found from '{origin}' to '{destination}'")

        options: list[RouteOption] = []
        weather_cond = "CLEAR"
        traffic_lvl = "NORMAL"
        avg_confidence = 0.88

        for idx, candidate in enumerate(candidates):
            # Run ML Prediction
            pred = self.prediction_service.predict_journey(
                base_travel_minutes=candidate.base_travel_minutes,
                distance_km=candidate.distance_km,
                num_stops=sum(leg.num_stops for leg in candidate.legs),
                mode_bus_ratio=candidate.mode_bus_ratio,
                transfers=candidate.transfers,
                departure_time=departure_time,
                location=origin,
            )

            weather_cond = pred.weather_condition
            traffic_lvl = pred.traffic_level
            avg_confidence = pred.confidence

            reliability = scoring_service.compute_reliability(
                delay_minutes=pred.delay_minutes,
                transfers=candidate.transfers,
                mode_bus_ratio=candidate.mode_bus_ratio,
            )

            # Calibrate crowd level & score by route type & modal character
            if candidate.route_type == "CALM":
                route_crowd_score = min(28, max(12, int(pred.crowd_score * 0.30)))
                route_crowd_level = "LOW"
            elif candidate.route_type == "OPTIMUM":
                route_crowd_score = min(58, max(36, int(pred.crowd_score * 0.55)))
                route_crowd_level = "MODERATE"
            elif candidate.route_type == "QUICKEST":
                route_crowd_score = max(78, min(95, pred.crowd_score))
                route_crowd_level = "VERY_HIGH" if route_crowd_score >= 88 else "HIGH"
            else:
                route_crowd_score = pred.crowd_score
                route_crowd_level = pred.crowd_level.value

            legs_schema = []
            for leg in candidate.legs:
                if (leg.mode or "").upper() == "WALK":
                    leg_crowd = "LOW"
                elif candidate.route_type == "CALM":
                    leg_crowd = "LOW"
                elif candidate.route_type == "OPTIMUM":
                    leg_crowd = "MODERATE" if (leg.mode or "").upper() == "METRO" else "LOW"
                else:
                    leg_crowd = route_crowd_level

                legs_schema.append(
                    JourneyLegSchema(
                        mode=leg.mode,
                        line=leg.line,
                        from_stop=leg.from_stop,
                        to_stop=leg.to_stop,
                        travel_minutes=leg.travel_minutes,
                        num_stops=leg.num_stops,
                        crowd_estimate=leg_crowd,
                        fare=leg.fare,
                    )
                )

            score = scoring_service.score_route(
                eta_minutes=pred.eta_minutes,
                waiting_minutes=candidate.base_waiting_minutes,
                delay_minutes=pred.delay_minutes,
                crowd_score=route_crowd_score,
                transfers=candidate.transfers,
                reliability=reliability,
            )

            options.append(
                RouteOption(
                    route_id=candidate.route_id,
                    route_name=candidate.route_name,
                    route_type=candidate.route_type,
                    eta_minutes=pred.eta_minutes,
                    waiting_minutes=candidate.base_waiting_minutes,
                    delay_minutes=pred.delay_minutes,
                    delay_risk=pred.delay_risk,
                    delay_probability=pred.delay_probability,
                    crowd_level=CrowdLevel(route_crowd_level),
                    crowd_score=route_crowd_score,
                    reliability=reliability,
                    transfers=candidate.transfers,
                    distance_km=candidate.distance_km,
                    fare=candidate.fare,
                    legs=legs_schema,
                    reason="",
                    score=score,
                )
            )

        # Sort: lowest score (best composite recommendation) first
        options.sort(key=lambda opt: opt.score if opt.score is not None else float("inf"))

        # Build explainable reasons
        for index, option in enumerate(options):
            option.reason = scoring_service.build_reason(
                is_recommended=(index == 0),
                route_type=option.route_type,
                eta_minutes=option.eta_minutes,
                crowd_level=option.crowd_level.value,
                delay_minutes=option.delay_minutes,
                transfers=option.transfers,
            )

        metadata = RecommendationMetadata(
            prediction_mode=PREDICTION_MODE,
            data_source="gtfs+ml-ensemble",
            confidence=avg_confidence,
            weather=weather_cond,
            traffic=traffic_lvl,
        )
        return options, metadata
