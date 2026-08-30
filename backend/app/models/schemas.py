"""
Pydantic models for API requests and responses.

Keeping these separate from business logic means the routing/prediction
services can be swapped out tomorrow (mock -> GTFS/ML) without touching
the API contract.
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


# ---------------------------------------------------------------------------
# Requests
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


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class RouteOption(BaseModel):
    route_id: str
    route_name: str
    eta_minutes: int
    waiting_minutes: int
    delay_minutes: int
    crowd_level: CrowdLevel
    crowd_score: int = Field(..., ge=0, le=100)
    reliability: float = Field(..., ge=0.0, le=1.0)
    transfers: int
    reason: str
    score: Optional[float] = Field(
        default=None,
        description="Internal scoring value used for ranking (lower is better).",
    )


class RecommendationMetadata(BaseModel):
    prediction_mode: str
    data_source: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class RecommendResponse(BaseModel):
    recommended_route: RouteOption
    alternatives: list[RouteOption]
    metadata: RecommendationMetadata


class RouteListResponse(BaseModel):
    routes: list[RouteOption]
    metadata: RecommendationMetadata


class HealthResponse(BaseModel):
    status: str
    service: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
