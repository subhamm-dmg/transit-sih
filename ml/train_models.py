"""
ml/train_models.py — Machine Learning training pipeline for TransitAI.

Trains lightweight, high-performance ML models for:
1. ETA Regression (predicts actual journey duration in minutes)
2. Delay Prediction (predicts delay in minutes & delay risk probability)
3. Crowding Estimation (predicts 0-100 crowd score and crowd level)

Saves trained model weights and metadata into ml/models/transit_models.json.
"""

import json
import math
from pathlib import Path
import numpy as np

MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
MODEL_FILE = MODELS_DIR / "transit_models.json"


def generate_synthetic_transit_dataset(n_samples: int = 15000, seed: int = 42):
    """
    Generates realistic transit observations anchored in urban Indian transit characteristics
    (DTC buses & Delhi Metro / Tier-1 & Tier-2 corridors).
    """
    np.random.seed(seed)

    # 1. Base route attributes
    distance_km = np.random.uniform(2.0, 35.0, n_samples)
    mode_bus_ratio = np.random.choice([1.0, 0.0, 0.5, 0.7, 0.3], size=n_samples, p=[0.55, 0.20, 0.12, 0.08, 0.05])
    transfers = np.random.choice([0, 1, 2], size=n_samples, p=[0.60, 0.32, 0.08])

    # Stops count loosely proportional to distance
    stops_per_km = np.where(mode_bus_ratio > 0.5, np.random.uniform(1.2, 2.2, n_samples), np.random.uniform(0.6, 1.1, n_samples))
    num_stops = np.clip((distance_km * stops_per_km).astype(int), 3, 45)

    # Scheduled travel time (base): Bus ~ 18-22 km/h scheduled, Metro ~ 35-40 km/h scheduled
    scheduled_speed_kmh = mode_bus_ratio * 20.0 + (1.0 - mode_bus_ratio) * 38.0
    base_travel_minutes = (distance_km / scheduled_speed_kmh * 60.0) + (transfers * 6.0)

    # 2. Environmental & Temporal Features
    hour = np.random.randint(5, 24, size=n_samples)  # 5 AM to 11 PM
    is_weekend = np.random.choice([0, 1], size=n_samples, p=[0.75, 0.25])

    # Peak hour indicators (Morning: 8-10 AM, Evening: 17-20 PM)
    morning_peak = ((hour >= 8) & (hour <= 10)).astype(float)
    evening_peak = ((hour >= 17) & (hour <= 20)).astype(float)
    peak_factor = np.where(is_weekend == 0, morning_peak * 1.35 + evening_peak * 1.45, 1.05)
    peak_factor = np.maximum(peak_factor, 1.0)

    # Traffic congestion factor (1.0 to 1.8 for bus, 1.0 for metro on grade-separated tracks)
    raw_traffic = 1.0 + (peak_factor - 1.0) * 1.2 + np.random.uniform(-0.05, 0.25, n_samples)
    traffic_factor = np.where(mode_bus_ratio > 0.3, np.clip(raw_traffic, 1.0, 1.9), 1.0 + 0.05 * np.random.uniform(0, 1, n_samples))

    # Weather (Rainfall in mm: 0 to 25mm)
    rain_mm = np.random.choice([0.0, 2.5, 8.0, 18.0], size=n_samples, p=[0.70, 0.15, 0.10, 0.05])
    weather_impact = (rain_mm / 10.0) * 0.18 * mode_bus_ratio

    # 3. Targets generation (Realistic Ground Truth)

    # Target 1: Delay in minutes
    base_delay = (
        (traffic_factor - 1.0) * 18.0 * mode_bus_ratio
        + (transfers * 3.5)
        + (weather_impact * 12.0)
        + (num_stops * 0.15 * (traffic_factor - 1.0))
        + np.random.normal(0, 1.5, n_samples)
    )
    delay_minutes = np.clip(base_delay, 0.0, 45.0)

    # Target 2: Actual Journey Time (ETA)
    eta_minutes = np.maximum(5.0, base_travel_minutes + delay_minutes + np.random.normal(0, 0.8, n_samples))

    # Target 3: Crowding Score (0 to 100)
    base_crowd = (
        (morning_peak * 42.0)
        + (evening_peak * 48.0)
        + (25.0 * (1.0 - is_weekend))
        + (mode_bus_ratio * 12.0)
        + (np.clip(distance_km / 35.0, 0, 1) * 10.0)
        + (weather_impact * 8.0)
        + np.random.normal(15, 8, n_samples)
    )
    crowd_score = np.clip(base_crowd, 5.0, 98.0)

    return {
        "features": {
            "base_travel_minutes": base_travel_minutes,
            "distance_km": distance_km,
            "num_stops": num_stops,
            "mode_bus_ratio": mode_bus_ratio,
            "transfers": transfers,
            "hour": hour,
            "is_weekend": is_weekend,
            "traffic_factor": traffic_factor,
            "rain_mm": rain_mm,
        },
        "targets": {
            "eta_minutes": eta_minutes,
            "delay_minutes": delay_minutes,
            "crowd_score": crowd_score,
        },
    }


def fit_linear_ridge(X: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> list[float]:
    """Fit Ridge linear regression model using normal equations: (X^T X + alpha*I)^(-1) X^T y"""
    n_features = X.shape[1]
    A = X.T @ X + alpha * np.eye(n_features)
    b = X.T @ y
    weights = np.linalg.solve(A, b)
    return weights.tolist()


def extract_feature_matrix(features_dict: dict) -> np.ndarray:
    """Build standardized non-linear feature matrix."""
    base = features_dict["base_travel_minutes"]
    dist = features_dict["distance_km"]
    stops = features_dict["num_stops"]
    bus_ratio = features_dict["mode_bus_ratio"]
    transfers = features_dict["transfers"]
    hour = features_dict["hour"]
    weekend = features_dict["is_weekend"]
    traffic = features_dict["traffic_factor"]
    rain = features_dict["rain_mm"]

    # Cyclic hour encoding
    hour_sin = np.sin(2 * np.pi * hour / 24.0)
    hour_cos = np.cos(2 * np.pi * hour / 24.0)

    # Peak flags
    is_peak = (((hour >= 8) & (hour <= 10)) | ((hour >= 17) & (hour <= 20))).astype(float)
    traffic_bus_interact = (traffic - 1.0) * bus_ratio
    rain_bus_interact = (rain / 10.0) * bus_ratio

    cols = [
        np.ones_like(base),  # Intercept
        base,
        dist,
        stops,
        bus_ratio,
        transfers,
        hour_sin,
        hour_cos,
        weekend,
        traffic,
        rain,
        is_peak,
        traffic_bus_interact,
        rain_bus_interact,
        (base * traffic_bus_interact),
        (stops * traffic_bus_interact),
    ]
    return np.column_stack(cols)


def train_and_save():
    print("Generating synthetic transit dataset...")
    data = generate_synthetic_transit_dataset(n_samples=25000)
    X = extract_feature_matrix(data["features"])

    eta_target = data["targets"]["eta_minutes"]
    delay_target = data["targets"]["delay_minutes"]
    crowd_target = data["targets"]["crowd_score"]

    print("Training ETA Prediction Model...")
    eta_weights = fit_linear_ridge(X, eta_target, alpha=1.0)
    eta_pred = X @ np.array(eta_weights)
    eta_mae = float(np.mean(np.abs(eta_pred - eta_target)))
    print(f"  ETA Model MAE: {eta_mae:.2f} minutes")

    print("Training Delay Prediction Model...")
    delay_weights = fit_linear_ridge(X, delay_target, alpha=1.0)
    delay_pred = X @ np.array(delay_weights)
    delay_mae = float(np.mean(np.abs(delay_pred - delay_target)))
    print(f"  Delay Model MAE: {delay_mae:.2f} minutes")

    print("Training Crowding Estimation Model...")
    crowd_weights = fit_linear_ridge(X, crowd_target, alpha=1.0)
    crowd_pred = X @ np.array(crowd_weights)
    crowd_mae = float(np.mean(np.abs(crowd_pred - crowd_target)))
    print(f"  Crowding Model MAE: {crowd_mae:.2f} points (0-100 scale)")

    model_payload = {
        "version": "1.0.0",
        "algorithm": "RidgeNonlinearEnsemble",
        "feature_names": [
            "intercept",
            "base_travel_minutes",
            "distance_km",
            "num_stops",
            "mode_bus_ratio",
            "transfers",
            "hour_sin",
            "hour_cos",
            "is_weekend",
            "traffic_factor",
            "rain_mm",
            "is_peak",
            "traffic_bus_interact",
            "rain_bus_interact",
            "base_traffic_interact",
            "stops_traffic_interact",
        ],
        "models": {
            "eta": {
                "weights": eta_weights,
                "mae": eta_mae,
            },
            "delay": {
                "weights": delay_weights,
                "mae": delay_mae,
            },
            "crowding": {
                "weights": crowd_weights,
                "mae": crowd_mae,
            },
        },
    }

    with open(MODEL_FILE, "w", encoding="utf-8") as f:
        json.dump(model_payload, f, indent=2)

    print(f"Models successfully trained and saved to: {MODEL_FILE}")


if __name__ == "__main__":
    train_and_save()
