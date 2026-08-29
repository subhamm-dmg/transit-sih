"""
Route scoring — combines travel time, waiting, delay, crowding,
transfers, and reliability into one comparable score per route.

Not in the original file tree but small enough to keep separate rather
than bury inside routing_service. Pure functions only, easy to tune.

Lower score = better route (used for ranking/sorting).
"""

# Tunable weights - simple, explainable, no ML here.
_WEIGHT_TRAVEL_TIME = 1.0
_WEIGHT_WAITING_TIME = 1.2
_WEIGHT_DELAY = 1.5
_WEIGHT_CROWD_SCORE = 0.3
_WEIGHT_TRANSFERS = 5.0
_WEIGHT_UNRELIABILITY = 20.0  # applied to (1 - reliability)


def compute_reliability(delay_minutes: int, transfers: int) -> float:
    """
    Deterministic mock reliability score in [0, 1].

    Simple rule: starts near-perfect, penalized by delay and transfers.
    Replace with a real historical-reliability model tomorrow.
    """
    penalty = (delay_minutes * 0.03) + (transfers * 0.08)
    reliability = max(0.0, min(1.0, 0.95 - penalty))
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
    Lower is better. Combines the factors linearly - simple and
    explainable, per the hackathon scope (no need for anything fancier
    tonight).
    """
    score = (
        eta_minutes * _WEIGHT_TRAVEL_TIME
        + waiting_minutes * _WEIGHT_WAITING_TIME
        + delay_minutes * _WEIGHT_DELAY
        + crowd_score * _WEIGHT_CROWD_SCORE
        + transfers * _WEIGHT_TRANSFERS
        + (1 - reliability) * _WEIGHT_UNRELIABILITY
    )
    return round(score, 2)


def build_reason(
    *,
    is_recommended: bool,
    eta_minutes: int,
    crowd_level: str,
    delay_minutes: int,
) -> str:
    """Short human-readable explanation for why a route ranked where it did."""
    if is_recommended:
        return f"Best balance of travel time, low crowding ({crowd_level}), and delay risk"
    if delay_minutes >= 7:
        return "Faster but higher predicted delay risk"
    if crowd_level in ("HIGH", "VERY_HIGH"):
        return "Faster but higher crowding"
    return "Alternative option with a different time/comfort trade-off"
