"""
PredictionService — the Prediction Engine.

Takes generic candidate-route info (works with today's mock RoutingService
AND tomorrow's Google Routes-backed RoutingService — this module never
imports or calls RoutingService/Google Routes directly) and produces:

    - eta_minutes / eta_confidence
    - delay_minutes / delay_confidence
    - crowd_level / crowd_score / crowd_confidence
    - prediction metadata (mode, data_source, timestamp)

Everything here is a DETERMINISTIC HEURISTIC, not a trained ML model.
prediction_mode is always reported as "heuristic" so nothing downstream
mistakes this for a real model. crowd_* values are explicitly
"estimated crowding" — we have no real occupancy data tonight.

Design goals (see project brief):
    - Never fail just because traffic/weather data is missing -> always
      fall back to pure time-of-day heuristics.
    - Stay decoupled from RoutingService's concrete route class -> takes
      a generic RouteInfo, with an adapter (`from_candidate`) for today's
      mock routes.
    - Leave room for live signals to override heuristics later, and for
      capacity-aware crowding (predicted_demand / capacity) later, without
      changing this module's public shape.
    - Route SCORING/ranking is NOT this service's job -> ScoringService
      still decides which route wins.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

PREDICTION_MODE = "heuristic"

# Peak hours used across ETA / delay / crowding heuristics. Simple and
# explainable on purpose - replace with a real calendar/holiday-aware
# model later if needed.
_PEAK_HOURS = {8, 9, 18, 19}
_SHOULDER_HOURS = {7, 10, 17, 20}

# Default vehicle capacity assumption for the (not-yet-wired-in)
# capacity-aware crowding formula: crowding = predicted_demand / capacity.
# Swap for real GTFS/vehicle-capacity data later.
DEFAULT_VEHICLE_CAPACITY = 60


class CrowdLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


# ---------------------------------------------------------------------------
# Generic inputs (decoupled from RoutingService's concrete classes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RouteInfo:
    """
    Generic route info the prediction engine needs. Any RoutingService
    implementation (today's mock network, tomorrow's Google Routes
    integration) can be adapted into this shape - see `from_candidate`.
    """

    route_id: str
    base_duration_minutes: int
    transfers: int
    departure_time: str
    route_type: str = "BUS"  # coarse mode hint: BUS / METRO / MIXED
    involves_major_hub: bool = False
    ridership_class: str = "normal"  # "normal" | "high_demand"
    base_duration_is_live: bool = False  # True once Google Routes is wired in

    @classmethod
    def from_candidate(cls, candidate) -> "RouteInfo":
        """
        Adapter for today's RoutingService.CandidateRoute (mock network).
        Duck-typed on purpose (reads attributes, doesn't import the class)
        so it keeps working if the teammate's Google Routes branch renames
        or restructures things slightly - update this one function, not
        the rest of the prediction engine.
        """
        route_name = getattr(candidate, "route_name", "") or ""
        legs = getattr(candidate, "legs", []) or []
        modes = {getattr(leg, "mode", "") for leg in legs}
        route_type = "MIXED" if len(modes) > 1 else (next(iter(modes), "BUS"))

        hub_keywords = ("majestic", "mg road", "silk board", "hub", "junction")
        involves_hub = any(k in route_name.lower() for k in hub_keywords)

        return cls(
            route_id=getattr(candidate, "route_id", "unknown"),
            base_duration_minutes=getattr(candidate, "base_travel_minutes", 30),
            transfers=getattr(candidate, "transfers", 0),
            departure_time="",  # filled in by caller (predict() takes it separately)
            route_type=route_type,
            involves_major_hub=involves_hub,
            ridership_class="normal",
            base_duration_is_live=False,
        )


@dataclass(frozen=True)
class LiveSignal:
    """
    Optional live/current signal that can override or nudge the heuristic
    prediction - the hook mentioned for "model drift" handling (road
    closures, disruptions, unexpected traffic) without an online-learning
    system. All fields optional; only supplied ones are applied.
    """

    delay_override_minutes: int | None = None
    crowd_score_override: int | None = None
    note: str | None = None


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PredictionResult:
    eta_minutes: int
    eta_confidence: float
    delay_minutes: int
    delay_confidence: float
    crowd_level: CrowdLevel
    crowd_score: int
    crowd_confidence: float
    prediction_mode: str
    data_source: str
    prediction_timestamp: str


# ---------------------------------------------------------------------------
# Prediction engine
# ---------------------------------------------------------------------------


class PredictionService:
    """
    Deterministic heuristic prediction engine. Gracefully degrades: works
    with zero optional inputs (no traffic/weather/historical data), and
    can use TrafficService/WeatherService results, or a LiveSignal
    override, when they're available and successfully retrieved.
    """

    def predict(
        self,
        route_info: RouteInfo,
        *,
        departure_time: str,
        is_weekend: bool = False,
        traffic_info=None,
        weather_info=None,
        live_signal: LiveSignal | None = None,
    ) -> PredictionResult:
        """
        Produce the full prediction bundle for one candidate route.

        traffic_info / weather_info are optional and consumed defensively:
        any missing field, wrong shape, or None simply falls back to the
        time-of-day heuristic - this method never raises because an
        optional data source was unavailable.
        """
        hour = self._parse_hour(departure_time)
        is_peak = hour in _PEAK_HOURS

        traffic_level, traffic_factor = self._read_traffic(traffic_info)
        weather_condition = self._read_weather(weather_info)

        delay_minutes, delay_confidence = self._predict_delay(
            is_peak=is_peak,
            traffic_level=traffic_level,
            weather_condition=weather_condition,
        )

        traffic_adjustment = self._traffic_adjustment_minutes(
            route_info.base_duration_minutes, traffic_factor, is_peak
        )

        crowd_score, crowd_confidence = self._predict_crowding(
            route_info=route_info, hour=hour, is_peak=is_peak, is_weekend=is_weekend
        )

        # --- live signal overrides (model-drift hook) -----------------
        data_sources = ["heuristic"]
        if traffic_info is not None:
            data_sources.append("traffic")
        if weather_info is not None:
            data_sources.append("weather")

        if live_signal is not None:
            if live_signal.delay_override_minutes is not None:
                delay_minutes = live_signal.delay_override_minutes
                delay_confidence = min(0.95, delay_confidence + 0.15)
                data_sources.append("live_signal")
            if live_signal.crowd_score_override is not None:
                crowd_score = max(0, min(100, live_signal.crowd_score_override))
                crowd_confidence = min(0.95, crowd_confidence + 0.15)
                if "live_signal" not in data_sources:
                    data_sources.append("live_signal")

        eta_minutes = max(1, route_info.base_duration_minutes + traffic_adjustment + delay_minutes)
        eta_confidence = self._confidence(
            base_is_live=route_info.base_duration_is_live,
            has_traffic=traffic_info is not None,
            has_weather=weather_info is not None,
        )

        crowd_level = self._score_to_level(crowd_score)

        return PredictionResult(
            eta_minutes=eta_minutes,
            eta_confidence=eta_confidence,
            delay_minutes=delay_minutes,
            delay_confidence=delay_confidence,
            crowd_level=crowd_level,
            crowd_score=crowd_score,
            crowd_confidence=crowd_confidence,
            prediction_mode=PREDICTION_MODE,
            data_source="+".join(data_sources),
            prediction_timestamp=datetime.now(UTC).isoformat(),
        )

    # -- ETA / traffic -------------------------------------------------

    @staticmethod
    def _traffic_adjustment_minutes(base_minutes: int, traffic_factor: float, is_peak: bool) -> int:
        """Extra minutes added on top of the base duration for traffic."""
        if traffic_factor is not None:
            return round(base_minutes * (traffic_factor - 1))
        # No traffic data at all -> fall back to a small peak-hour bump.
        return round(base_minutes * 0.1) if is_peak else 0

    # -- delay -----------------------------------------------------------

    @staticmethod
    def _predict_delay(*, is_peak: bool, traffic_level, weather_condition) -> tuple[int, float]:
        """
        Simple explainable delay heuristic:
            off-peak -> low base delay, peak -> higher base delay
            + traffic bump if traffic data says HEAVY/MODERATE
            + weather bump if RAIN/HEAVY_RAIN
        """
        delay = 6 if is_peak else 2
        confidence = 0.55 if is_peak else 0.6

        if traffic_level == "HEAVY":
            delay += 4
            confidence += 0.15
        elif traffic_level == "MODERATE":
            delay += 2
            confidence += 0.1
        # traffic_level is None -> no bump, no confidence bonus (missing data)

        if weather_condition == "HEAVY_RAIN":
            delay += 4
            confidence += 0.1
        elif weather_condition == "RAIN":
            delay += 2
            confidence += 0.05
        # weather_condition is None -> no bump, no confidence bonus

        delay = min(delay, 25)
        confidence = round(min(confidence, 0.9), 2)
        return delay, confidence

    # -- crowding ----------------------------------------------------------

    @staticmethod
    def _predict_crowding(*, route_info: RouteInfo, hour: int, is_peak: bool, is_weekend: bool) -> tuple[int, float]:
        """
        Deterministic, explainable "estimated crowding" score (0-100).
        NOT real occupancy - we have no live occupancy feed tonight.

        weekday peak + major hub + high-demand route -> pushes score up.
        weekend / off-peak -> pushes score down.
        """
        score = 15  # baseline

        if is_weekend:
            score += 5 if is_peak else 2
        else:
            if is_peak:
                score += 40
            elif hour in _SHOULDER_HOURS:
                score += 20
            else:
                score += 8

        if route_info.involves_major_hub:
            score += 15
        if route_info.ridership_class == "high_demand":
            score += 12
        score += route_info.transfers * 5

        score = max(0, min(100, score))

        # We never have real occupancy data, so confidence is deliberately
        # capped low even in the best case - this is an estimate.
        confidence = 0.55 if (is_peak and not is_weekend) else 0.4
        return score, round(confidence, 2)

    @staticmethod
    def _score_to_level(score: int) -> CrowdLevel:
        if score <= 30:
            return CrowdLevel.LOW
        if score <= 55:
            return CrowdLevel.MODERATE
        if score <= 80:
            return CrowdLevel.HIGH
        return CrowdLevel.VERY_HIGH

    # -- confidence -----------------------------------------------------

    @staticmethod
    def _confidence(*, base_is_live: bool, has_traffic: bool, has_weather: bool) -> float:
        score = 0.5
        if base_is_live:
            score += 0.15
        if has_traffic:
            score += 0.2
        if has_weather:
            score += 0.1
        return round(min(score, 0.95), 2)

    # -- optional-data readers (never raise) -----------------------------

    @staticmethod
    def _read_traffic(traffic_info) -> tuple[str | None, float | None]:
        """Defensively read a TrafficService result. Returns (level, factor)."""
        if traffic_info is None:
            return None, None
        try:
            level = getattr(traffic_info, "level", None)
            level_name = getattr(level, "value", level)  # enum or plain str
            factor = getattr(traffic_info, "delay_factor", None)
            return level_name, factor
        except Exception:
            return None, None

    @staticmethod
    def _read_weather(weather_info) -> str | None:
        """Defensively read a WeatherService result. Returns condition name."""
        if weather_info is None:
            return None
        try:
            condition = getattr(weather_info, "condition", None)
            return getattr(condition, "value", condition)
        except Exception:
            return None

    @staticmethod
    def _parse_hour(departure_time: str) -> int:
        try:
            return int(departure_time.split(":")[0])
        except (ValueError, IndexError, AttributeError):
            return 12


# ---------------------------------------------------------------------------
# Capacity-aware crowding (not wired in yet - future use)
# ---------------------------------------------------------------------------


def estimate_crowding_from_demand(
    predicted_demand: float, capacity: int = DEFAULT_VEHICLE_CAPACITY
) -> int:
    """
    crowding = predicted_demand / estimated_capacity, expressed 0-100.

    Not called anywhere yet - this is the documented seam for plugging in
    real predicted-demand + real vehicle-capacity data later (GTFS,
    historical ridership, live occupancy feeds) without redesigning
    PredictionService. `capacity` defaults to DEFAULT_VEHICLE_CAPACITY
    when real capacity data isn't available.
    """
    if capacity <= 0:
        capacity = DEFAULT_VEHICLE_CAPACITY
    ratio = predicted_demand / capacity
    return max(0, min(100, round(ratio * 100)))
