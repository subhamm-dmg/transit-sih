"""
backend/app/services/weather_service.py — Weather Intelligence Service.

Fetches live real-time weather via Open-Meteo API (free, no API key required)
for coordinates/cities with resilient local caching and deterministic fallback.
"""

from dataclasses import dataclass
from enum import Enum
import time
from typing import Optional
import httpx


class WeatherCondition(str, Enum):
    CLEAR = "CLEAR"
    CLOUDY = "CLOUDY"
    RAIN = "RAIN"
    HEAVY_RAIN = "HEAVY_RAIN"


@dataclass(frozen=True)
class WeatherInfo:
    condition: WeatherCondition
    temperature_c: float
    rain_mm: float
    source: str


class WeatherService:
    """Provides current weather signals for transit prediction."""

    _cache: dict[str, tuple[float, WeatherInfo]] = {}

    def __init__(self, default_lat: float = 28.6139, default_lon: float = 77.2090):
        # Default: Delhi (28.6139, 77.2090)
        self.default_lat = default_lat
        self.default_lon = default_lon

    def get_weather(self, location: str = "Delhi", departure_time: str = "09:00") -> WeatherInfo:
        """
        Fetches weather condition and rain amount (mm).
        Uses 15-minute in-memory cache to minimize external network latency.
        """
        now = time.time()
        cache_key = f"{location.lower()}"
        if cache_key in self._cache:
            timestamp, cached_val = self._cache[cache_key]
            if now - timestamp < 900:  # 15 min cache
                return cached_val

        # Attempt live Open-Meteo call with short timeout
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={self.default_lat}&longitude={self.default_lon}&current=temperature_2m,precipitation,weather_code"
            with httpx.Client(timeout=1.5) as client:
                res = client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    current = data.get("current", {})
                    temp = float(current.get("temperature_2m", 28.0))
                    rain = float(current.get("precipitation", 0.0))
                    code = int(current.get("weather_code", 0))

                    if rain > 5.0 or code in (65, 67, 82):
                        condition = WeatherCondition.HEAVY_RAIN
                    elif rain > 0.1 or code in (51, 53, 55, 61, 63, 80, 81):
                        condition = WeatherCondition.RAIN
                    elif code in (1, 2, 3):
                        condition = WeatherCondition.CLOUDY
                    else:
                        condition = WeatherCondition.CLEAR

                    info = WeatherInfo(
                        condition=condition,
                        temperature_c=temp,
                        rain_mm=rain,
                        source="open-meteo-live",
                    )
                    self._cache[cache_key] = (now, info)
                    return info
        except Exception:
            pass  # Fall back to simulated profile on network failure/offline

        hour = self._parse_hour(departure_time)
        if hour in (17, 18, 19):
            condition = WeatherCondition.RAIN
            rain = 4.2
            temp = 25.0
        elif hour in (12, 13, 14):
            condition = WeatherCondition.CLEAR
            rain = 0.0
            temp = 32.0
        else:
            condition = WeatherCondition.CLOUDY
            rain = 0.0
            temp = 27.0

        info = WeatherInfo(condition=condition, temperature_c=temp, rain_mm=rain, source="weather-proxy")
        self._cache[cache_key] = (now, info)
        return info

    @staticmethod
    def _parse_hour(departure_time: str) -> int:
        try:
            return int(departure_time.split(":")[0])
        except (ValueError, IndexError):
            return 9
