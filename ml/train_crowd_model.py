"""
Offline training script for the crowd prediction model.

Adapted from the crowd_estimate.py prototype supplied for this
integration - not run automatically, not imported by the backend. Kept
here for reproducibility (how backend/app/ml/artifacts/crowd_model.pkl
was produced) and so someone can retrain on a better dataset later.

Run manually from the repo root:
    python ml/train_crowd_model.py

Imports the feature schema from backend/app/ml/features.py instead of
redefining it, so training-time and serving-time features can't drift
apart (the original prototype defined FEATURES separately in two files
and relied on a code comment to keep them in sync).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Reuse the backend's feature schema instead of duplicating it.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.ml.features import FEATURES, is_rush_hour, is_weekend  # noqa: E402

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "ml" / "synthetic_transit_data.csv"
MODEL_OUT = Path(__file__).resolve().parent.parent / "backend" / "app" / "ml" / "artifacts" / "crowd_model.pkl"
TARGET = "crowd_level"


def main() -> None:
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    from sklearn.model_selection import train_test_split
    import joblib

    data = pd.read_csv(DATA_PATH)

    # Derived columns - same rule as app.ml.features so training matches serving.
    data["is_weekend"] = data["day_of_week"].apply(is_weekend)
    data["is_rush_hour"] = data["time_of_day"].apply(is_rush_hour)

    X, y = data[FEATURES], data[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = HistGradientBoostingRegressor(
        learning_rate=0.05,
        max_iter=300,
        max_leaf_nodes=31,
        l2_regularization=1.0,
        random_state=42,
    )
    model.fit(X_train, y_train)

    pred = np.clip(model.predict(X_test), 0, 1000)
    print("MAE :", mean_absolute_error(y_test, pred))
    print("RMSE:", mean_squared_error(y_test, pred) ** 0.5)

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_OUT)
    print(f"Model saved to {MODEL_OUT}")


if __name__ == "__main__":
    main()
