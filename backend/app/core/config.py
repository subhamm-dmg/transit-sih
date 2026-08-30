"""
Application configuration.

Loaded from environment variables (via .env in local dev). No hardcoded
secrets. Every value has a safe default so the app runs fully offline
without a .env file.
"""

from __future__ import annotations

import os
from functools import lru_cache

try:
    # Optional: load a local .env file if python-dotenv is installed.
    # Not required for the app to run.
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


class Settings:
    """Central place for all configuration values."""

    APP_NAME: str = os.getenv("APP_NAME", "transit-sih-backend")
    ENV: str = os.getenv("ENV", "development")

    # CORS - local frontend dev servers
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
    ).split(",")

    # Feature flags for swapping mock adapters -> real integrations later.
    # Everything defaults to "mock" so the backend works fully offline.
    ROUTING_MODE: str = os.getenv("ROUTING_MODE", "mock")
    PREDICTION_MODE: str = os.getenv("PREDICTION_MODE", "mock")
    TRAFFIC_MODE: str = os.getenv("TRAFFIC_MODE", "mock")
    WEATHER_MODE: str = os.getenv("WEATHER_MODE", "mock")

    from typing import Optional

    WEATHER_API_KEY: Optional[str] = os.getenv("WEATHER_API_KEY")
    TRAFFIC_API_KEY: Optional[str] = os.getenv("TRAFFIC_API_KEY")
    GTFS_DATA_PATH: Optional[str] = os.getenv("GTFS_DATA_PATH")


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (avoids re-parsing env on every import)."""
    return Settings()
