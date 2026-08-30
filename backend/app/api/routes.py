"""
backend/app/api/routes.py — Routes and Stop Autocomplete API.
"""

from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import RecommendRequest, RouteListResponse, RouteOption, StopItem, StopSearchResponse
from app.services.recommendation_service import RecommendationService
from app.services.routing_service import RouteNotFoundError, RoutingService

router = APIRouter(tags=["routes"])
_recommendation_service = RecommendationService()
_routing_service = RoutingService()


@router.get("/stops/search", response_model=StopSearchResponse)
def search_stops(
    q: str = Query("", description="Query string for stop name autocomplete"),
    limit: int = Query(8, ge=1, le=50, description="Max results"),
) -> StopSearchResponse:
    """Fuzzy/prefix search for stops across the GTFS network."""
    results = _routing_service.search_stops(q, limit=limit)
    return StopSearchResponse(stops=[StopItem(name=item["name"]) for item in results])


@router.get("/routes", response_model=RouteListResponse)
def list_candidate_routes(
    from_: str = Query(..., alias="from", min_length=1),
    to: str = Query(..., min_length=1),
    departure_time: str = Query("09:00"),
) -> RouteListResponse:
    try:
        RecommendRequest(**{"from": from_, "to": to, "departure_time": departure_time})
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid request: {exc}") from exc

    try:
        options, metadata = _recommendation_service.get_ranked_routes(from_, to, departure_time)
    except RouteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return RouteListResponse(routes=options, metadata=metadata)


@router.get("/routes/{route_id}", response_model=RouteOption)
def get_route_detail(
    route_id: str,
    from_: str = Query(..., alias="from", min_length=1),
    to: str = Query(..., min_length=1),
    departure_time: str = Query("09:00"),
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
