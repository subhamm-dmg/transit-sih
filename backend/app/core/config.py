"""
Application configuration.

Loaded from environment variables (via .env in local dev). No hardcoded
secrets. Every value has a safe default so the app runs fully offline
without a .env file.
"""

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
    """
    Central place for all configuration values.

    Read in __init__ (not as class-level attributes) so each Settings()
    instantiation picks up the current environment - important for tests
    that need to flip a mode (e.g. ROUTING_MODE) within one process via
    monkeypatch + get_settings.cache_clear(). Real app startup is
    unaffected either way, since .env is loaded once, before the first
    Settings() is created.
    """

    def __init__(self) -> None:
        self.APP_NAME: str = os.getenv("APP_NAME", "transit-sih-backend")
        self.ENV: str = os.getenv("ENV", "development")

        # CORS - local frontend dev servers
        self.CORS_ORIGINS: list[str] = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173",
        ).split(",")

        # Feature flags for swapping mock adapters -> real integrations later.
        # Everything defaults to "mock" so the backend works fully offline.
        self.ROUTING_MODE: str = os.getenv("ROUTING_MODE", "mock")
        self.PREDICTION_MODE: str = os.getenv("PREDICTION_MODE", "mock")
        self.TRAFFIC_MODE: str = os.getenv("TRAFFIC_MODE", "mock")
        self.WEATHER_MODE: str = os.getenv("WEATHER_MODE", "mock")

        # Placeholders for tomorrow's real integrations. Never hardcode keys;
        # these just read from env and stay unset (None) tonight.
        self.WEATHER_API_KEY: str | None = os.getenv("WEATHER_API_KEY")
        self.TRAFFIC_API_KEY: str | None = os.getenv("TRAFFIC_API_KEY")
        self.GTFS_DATA_PATH: str | None = os.getenv("GTFS_DATA_PATH")
        # Not read anywhere yet - GoogleRoutesProvider is a stub. Placeholder
        # only, so the env var name is settled when that provider is built.
        self.GOOGLE_ROUTES_API_KEY: str | None = os.getenv("GOOGLE_ROUTES_API_KEY")


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (avoids re-parsing env on every import)."""
    return Settings()
