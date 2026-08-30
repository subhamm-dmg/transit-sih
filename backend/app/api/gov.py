"""
backend/app/api/gov.py — Transport Authority / Government Intelligence API Endpoints.
"""

from fastapi import APIRouter, Query
from app.models.schemas import (
    CorridorMetrics,
    GovAlert,
    GovDemandResponse,
    GovOverviewResponse,
    SimulateActionRequest,
    SimulateActionResponse,
)
from app.services.gov_service import GovernmentService

router = APIRouter(prefix="/gov", tags=["government"])
_gov_service = GovernmentService()


@router.get("/overview", response_model=GovOverviewResponse)
def get_gov_overview() -> GovOverviewResponse:
    """Network-wide stress, delay hotspots, and fleet monitoring overview."""
    return _gov_service.get_overview()


@router.get("/corridors", response_model=list[CorridorMetrics])
def list_corridors() -> list[CorridorMetrics]:
    """Corridor-by-corridor demand, delay, crowding, and financial performance."""
    return _gov_service.get_corridors()


@router.get("/demand", response_model=GovDemandResponse)
def get_demand_forecast(
    peak_window: str = Query("08:00 – 10:00 AM", description="Selected peak operational window")
) -> GovDemandResponse:
    """Hourly ridership load distribution and 60-minute predictive forecast."""
    return _gov_service.get_demand(peak_window=peak_window)


@router.get("/alerts", response_model=list[GovAlert])
def get_gov_alerts() -> list[GovAlert]:
    """Active anomaly alerts, bottleneck warnings, and recommended actions."""
    return _gov_service.get_alerts()


@router.post("/simulate-action", response_model=SimulateActionResponse)
def simulate_action(payload: SimulateActionRequest) -> SimulateActionResponse:
    """Simulate the projected operational impact of a transit policy intervention."""
    return _gov_service.simulate_action(action_type=payload.action_type, corridor_id=payload.corridor_id)
