"""
backend/app/services/traffic_service.py — Traffic & Congestion Intelligence Service.

Estimates real-time road congestion factors and delay multipliers
for bus routes and multi-modal corridors based on peak-hour congestion profiles.
"""

from dataclasses import dataclass
from enum import Enum


class TrafficLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HEAVY = "HEAVY"
    SEVERE = "SEVERE"


@dataclass(frozen=True)
class TrafficInfo:
    level: TrafficLevel
    congestion_factor: float  # Multiplier on road transit travel time (e.g. 1.0 - 1.8)
    delay_risk_score: int  # 0 - 100
    source: str


class TrafficService:
    """Calculates traffic congestion index for transit routes."""

    def get_traffic_level(self, stop_or_area: str, departure_time: str, is_weekend: bool = False) -> TrafficInfo:
        hour = self._parse_hour(departure_time)

        # Peak hours: Morning (8:00 - 10:30), Evening (17:00 - 20:30)
        if not is_weekend:
            if (8 <= hour <= 10) or (17 <= hour <= 19):
                return TrafficInfo(
                    level=TrafficLevel.SEVERE if hour in (9, 18) else TrafficLevel.HEAVY,
                    congestion_factor=1.45 if hour in (9, 18) else 1.32,
                    delay_risk_score=85 if hour in (9, 18) else 72,
                    source="traffic-intelligence-engine",
                )
            elif (7 <= hour <= 8) or (11 <= hour <= 12) or (16 <= hour <= 17) or (20 <= hour <= 21):
                return TrafficInfo(
                    level=TrafficLevel.MODERATE,
                    congestion_factor=1.18,
                    delay_risk_score=48,
                    source="traffic-intelligence-engine",
                )
            else:
                return TrafficInfo(
                    level=TrafficLevel.LOW,
                    congestion_factor=1.04,
                    delay_risk_score=15,
                    source="traffic-intelligence-engine",
                )
        else:
            # Weekend pattern: Moderate afternoon/evening leisure traffic
            if 14 <= hour <= 20:
                return TrafficInfo(
                    level=TrafficLevel.MODERATE,
                    congestion_factor=1.15,
                    delay_risk_score=38,
                    source="traffic-intelligence-engine",
                )
            return TrafficInfo(
                level=TrafficLevel.LOW,
                congestion_factor=1.02,
                delay_risk_score=10,
                source="traffic-intelligence-engine",
            )

    @staticmethod
    def _parse_hour(departure_time: str) -> int:
        try:
            return int(departure_time.split(":")[0])
        except (ValueError, IndexError):
            return 9
