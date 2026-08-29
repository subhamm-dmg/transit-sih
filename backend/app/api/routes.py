"""
GET /api/routes
GET /api/routes/{route_id}
"""

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import RouteListResponse, RouteOption
from app.models.schemas import RecommendRequest
from app.services.recommendation_service import RecommendationService
from app.services.routing_service import RouteNotFoundError

router = APIRouter(tags=["routes"])
_recommendation_service = RecommendationService()


@router.get("/routes", response_model=RouteListResponse)
def list_candidate_routes(
    from_: str = Query(..., alias="from", min_length=1),
    to: str = Query(..., min_length=1),
    departure_time: str = Query(...),
) -> RouteListResponse:
    # Reuse the same validation as /api/recommend for consistency.
    try:
        RecommendRequest(**{"from": from_, "to": to, "departure_time": departure_time})
    except Exception as exc:  # pydantic ValidationError
        raise HTTPException(status_code=422, detail=f"Invalid request: {exc}") from exc

    try:
        options, metadata = _recommendation_service.get_ranked_routes(
            from_, to, departure_time
        )
    except RouteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return RouteListResponse(routes=options, metadata=metadata)


@router.get("/routes/{route_id}", response_model=RouteOption)
def get_route_detail(
    route_id: str,
    from_: str = Query(..., alias="from", min_length=1),
    to: str = Query(..., min_length=1),
    departure_time: str = Query(...),
) -> RouteOption:
    try:
        RecommendRequest(**{"from": from_, "to": to, "departure_time": departure_time})
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid request: {exc}") from exc

    try:
        options, _ = _recommendation_service.get_ranked_routes(from_, to, departure_time)
    except RouteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    for option in options:
        if option.route_id == route_id:
            return option

    raise HTTPException(status_code=404, detail=f"Route '{route_id}' not found")
