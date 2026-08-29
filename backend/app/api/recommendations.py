"""POST /api/recommend"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import RecommendRequest, RecommendResponse
from app.services.recommendation_service import RecommendationService
from app.services.routing_service import RouteNotFoundError

router = APIRouter(tags=["recommendations"])
_recommendation_service = RecommendationService()


@router.post("/recommend", response_model=RecommendResponse)
def recommend_route(request: RecommendRequest) -> RecommendResponse:
    try:
        options, metadata = _recommendation_service.get_ranked_routes(
            request.from_, request.to, request.departure_time
        )
    except RouteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # safety net - unexpected internal error
        raise HTTPException(status_code=500, detail="Internal error computing recommendation") from exc

    if not options:
        raise HTTPException(status_code=404, detail="No routes found")

    recommended, *alternatives = options
    return RecommendResponse(
        recommended_route=recommended,
        alternatives=alternatives,
        metadata=metadata,
    )
