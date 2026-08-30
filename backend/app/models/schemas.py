"""
backend/app/models/schemas.py — Pydantic API Models.

Defines the API contracts for Route Recommendation, Stop Search, and Government Analytics.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class CrowdLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class DelayRisk(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Commuter API Schemas
# ---------------------------------------------------------------------------


class RecommendRequest(BaseModel):
    from_: str = Field(..., alias="from", min_length=1, description="Origin stop name")
    to: str = Field(..., min_length=1, description="Destination stop name")
    departure_time: str = Field(..., description="Departure time as HH:MM (24h)")

    model_config = {"populate_by_name": True}

    @field_validator("departure_time")
    @classmethod
    def validate_departure_time(cls, value: str) -> str:
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError("departure_time must be in HH:MM format")
        hour_str, minute_str = parts
        if not (hour_str.isdigit() and minute_str.isdigit()):
            raise ValueError("departure_time must be in HH:MM format")
        hour, minute = int(hour_str), int(minute_str)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("departure_time must be a valid 24h time (HH:MM)")
        return f"{hour:02d}:{minute:02d}"


class JourneyLegSchema(BaseModel):
    mode: str = Field(..., description="'WALK', 'BUS', or 'METRO'")
    line: str
    from_stop: str
    to_stop: str
    travel_minutes: int
    num_stops: int = 0
    crowd_estimate: str = "MODERATE"
    fare: int = 0


class RouteOption(BaseModel):
    route_id: str
    route_name: str
    route_type: str = Field("OPTIMUM", description="'OPTIMUM', 'QUICKEST', or 'CALM'")
    eta_minutes: int
    waiting_minutes: int
    delay_minutes: int
    delay_risk: str = "LOW"
    delay_probability: float = 0.15
    crowd_level: CrowdLevel
    crowd_score: int = Field(..., ge=0, le=100)
    reliability: float = Field(..., ge=0.0, le=1.0)
    transfers: int
    distance_km: float = 0.0
    fare: int = 25
    legs: list[JourneyLegSchema] = Field(default_factory=list)
    reason: str
    score: Optional[float] = Field(
        default=None,
        description="Internal multi-objective scoring value (lower is better)",
    )


class RecommendationMetadata(BaseModel):
    prediction_mode: str
    data_source: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    weather: str = "CLEAR"
    traffic: str = "NORMAL"


class RecommendResponse(BaseModel):
    recommended_route: RouteOption
    alternatives: list[RouteOption]
    metadata: RecommendationMetadata


class RouteListResponse(BaseModel):
    routes: list[RouteOption]
    metadata: RecommendationMetadata


class StopItem(BaseModel):
    name: str


class StopSearchResponse(BaseModel):
    stops: list[StopItem]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    stops_indexed: int
    routes_indexed: int
    ml_models_loaded: bool


# ---------------------------------------------------------------------------
# Government Analytics API Schemas
# ---------------------------------------------------------------------------


class CorridorMetrics(BaseModel):
    id: str
    name: str
    color: str
    time: int
    demand: int
    crowd: int
    delay: int
    reliability: int
    revenue: int
    transfers: int
    type: str
    score: int
    path: list[str]


class GovOverviewResponse(BaseModel):
    delay_hotspots: int
    high_demand_routes: int
    critical_corridors: int
    network_load_pct: int
    avg_delay_min: int
    peak_demand_per_hour: int
    active_fleet_count: int


class GovDemandPoint(BaseModel):
    time: str
    demand_index: int


class GovDemandResponse(BaseModel):
    peak_window: str
    current_load: int
    avg_delay: int
    peak_demand: int
    hourly_distribution: list[GovDemandPoint]
    forecast_60min: str


class GovAlert(BaseModel):
    id: str
    priority: str
    title: str
    description: str
    corridor: str
    suggested_action: str


class SimulateActionRequest(BaseModel):
    action_type: str = Field(..., description="'frequency', 'deploy_bus', or 'reroute'")
    corridor_id: str = "R9"


class SimulateActionResponse(BaseModel):
    action_type: str
    corridor_id: str
    before_load: int
    after_load: int
    before_delay: int
    after_delay: int
    estimated_impact: str
    roi_score: float
