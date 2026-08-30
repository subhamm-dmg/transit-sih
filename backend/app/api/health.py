"""
backend/app/api/health.py — System Health & Service Status.
"""

from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.services.gtfs_loader import GTFSNetwork
from ml.inference import MLInferenceEngine

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    network = GTFSNetwork.get_instance()
    ml_engine = MLInferenceEngine.get_instance()

    return HealthResponse(
        status="ok",
        service="transit-sih-backend",
        version="1.0.0",
        stops_indexed=len(network.stops),
        routes_indexed=len(network.routes),
        ml_models_loaded=ml_engine.is_loaded,
    )
