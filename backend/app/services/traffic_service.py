"""
TrafficService — traffic / congestion proxy information.

Tonight this returns deterministic mock data. Not currently wired into
scoring (kept simple per the MVP scope), but available for
PredictionService or scoring to consume tomorrow.

Swap-out plan for tomorrow:
    Replace get_traffic_level() with a real call to a traffic API
    (e.g. Google/HERE/TomTom), using TRAFFIC_API_KEY from config.
"""

from dataclasses import dataclass
from enum import Enum


class TrafficLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HEAVY = "HEAVY"


@dataclass(frozen=True)
class TrafficInfo:
    level: TrafficLevel
    delay_factor: float  # multiplier to apply to base travel time
    source: str


class TrafficService:
    """Deterministic mock stand-in for a real traffic data provider."""

    def get_traffic_level(self, stop_or_area: str, departure_time: str) -> TrafficInfo:
        hour = self._parse_hour(departure_time)
        if hour in (8, 9, 18, 19):
            return TrafficInfo(level=TrafficLevel.HEAVY, delay_factor=1.25, source="mock")
        if hour in (7, 10, 17, 20):
            return TrafficInfo(level=TrafficLevel.MODERATE, delay_factor=1.1, source="mock")
        return TrafficInfo(level=TrafficLevel.LOW, delay_factor=1.0, source="mock")

    @staticmethod
    def _parse_hour(departure_time: str) -> int:
        try:
            return int(departure_time.split(":")[0])
        except (ValueError, IndexError):
            return 12
