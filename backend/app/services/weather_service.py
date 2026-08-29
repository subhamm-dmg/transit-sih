"""
WeatherService — weather conditions relevant to journey planning.

Tonight this returns deterministic mock data. Not currently wired into
scoring (kept simple per the MVP scope), but available for
PredictionService or scoring to consume tomorrow.

Swap-out plan for tomorrow:
    Replace get_weather() with a real call to Open-Meteo (or similar),
    using WEATHER_API_KEY from config if the chosen provider needs one.
"""

from dataclasses import dataclass
from enum import Enum


class WeatherCondition(str, Enum):
    CLEAR = "CLEAR"
    CLOUDY = "CLOUDY"
    RAIN = "RAIN"
    HEAVY_RAIN = "HEAVY_RAIN"


@dataclass(frozen=True)
class WeatherInfo:
    condition: WeatherCondition
    temperature_c: float
    source: str


class WeatherService:
    """Deterministic mock stand-in for a real weather data provider."""

    def get_weather(self, location: str, departure_time: str) -> WeatherInfo:
        hour = self._parse_hour(departure_time)
        # Simple deterministic pattern: "rainy evenings" for demo variety.
        if hour in (17, 18, 19):
            condition = WeatherCondition.RAIN
            temp = 22.0
        elif hour in (12, 13, 14):
            condition = WeatherCondition.CLEAR
            temp = 30.0
        else:
            condition = WeatherCondition.CLOUDY
            temp = 26.0

        return WeatherInfo(condition=condition, temperature_c=temp, source="mock")

    @staticmethod
    def _parse_hour(departure_time: str) -> int:
        try:
            return int(departure_time.split(":")[0])
        except (ValueError, IndexError):
            return 12
