"""
backend/app/services/scoring_service.py — Multi-Objective Route Scoring & Reason Generation.

Combines predicted travel time, waiting time, predicted delay, crowding,
transfers, and reliability into a unified ranking score (lower is better).
"""

# Tunable weights
_WEIGHT_TRAVEL_TIME = 1.0
_WEIGHT_WAITING_TIME = 1.2
_WEIGHT_DELAY = 1.6
_WEIGHT_CROWD_SCORE = 0.35
_WEIGHT_TRANSFERS = 6.0
_WEIGHT_UNRELIABILITY = 25.0


def compute_reliability(delay_minutes: int, transfers: int, mode_bus_ratio: float = 1.0) -> float:
    """
    Computes reliability score in [0.0, 1.0].
    Rail/Metro has higher intrinsic reliability, while multi-transfer bus journeys
    accumulate higher variability.
    """
    bus_penalty = mode_bus_ratio * 0.04
    delay_penalty = delay_minutes * 0.025
    transfer_penalty = transfers * 0.06
    reliability = max(0.40, min(0.99, 0.98 - bus_penalty - delay_penalty - transfer_penalty))
    return round(reliability, 2)


def score_route(
    *,
    eta_minutes: int,
    waiting_minutes: int,
    delay_minutes: int,
    crowd_score: int,
    transfers: int,
    reliability: float,
) -> float:
    """
    Calculates multi-objective scalar penalty (lower score = higher recommendation rank).
    """
    score = (
        eta_minutes * _WEIGHT_TRAVEL_TIME
        + waiting_minutes * _WEIGHT_WAITING_TIME
        + delay_minutes * _WEIGHT_DELAY
        + crowd_score * _WEIGHT_CROWD_SCORE
        + transfers * _WEIGHT_TRANSFERS
        + (1.0 - reliability) * _WEIGHT_UNRELIABILITY
    )
    return round(score, 2)


def build_reason(
    *,
    is_recommended: bool,
    route_type: str,
    eta_minutes: int,
    crowd_level: str,
    delay_minutes: int,
    transfers: int,
) -> str:
    """Generates user-friendly explanations for route recommendations."""
    if is_recommended:
        if crowd_level in ("LOW", "MODERATE") and delay_minutes <= 4:
            return f"ML Recommended: Optimal balance of ETA ({eta_minutes}m), light crowding ({crowd_level}), and minimal delay risk."
        return f"ML Recommended: Best composite score balancing journey time ({eta_minutes}m) against network crowding."

    if route_type == "QUICKEST":
        return f"Quickest option ({eta_minutes}m), but carries higher crowd density ({crowd_level})."

    if route_type == "CALM" or crowd_level == "LOW":
        return f"Least crowded option ({crowd_level}) for comfortable seating, with slightly longer transit time."

    if delay_minutes >= 7:
        return f"Higher predicted delay (+{delay_minutes}m) due to corridor bottlenecks."

    if transfers == 0:
        return "Direct single-leg route without interchange hassle."

    return "Alternative connection providing different trade-offs in speed and comfort."
