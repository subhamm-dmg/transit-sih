"""
Government transport insights API.

All endpoints are additive under /api/insights.
They do not interact with route prediction/scoring.
"""

from fastapi import APIRouter

from app.services.analytics_service import AnalyticsService

router = APIRouter(
    prefix="/insights",
    tags=["government-insights"],
)

_analytics_service = AnalyticsService()


@router.get("/summary")
def get_summary() -> dict:
    return _analytics_service.summary()


@router.get("/demand")
def get_demand() -> dict:
    return _analytics_service.demand()


@router.get("/delays")
def get_delays() -> dict:
    return _analytics_service.delays()


@router.get("/crowding")
def get_crowding() -> dict:
    return _analytics_service.crowding()


@router.get("/bottlenecks")
def get_bottlenecks() -> dict:
    return _analytics_service.bottlenecks()
