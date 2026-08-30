# Crowd prediction ML component

## What's real vs. mock

| Prediction | Status | Why |
|---|---|---|
| Crowding | **Real ML** (`HistGradientBoostingRegressor`), with automatic mock fallback if the model fails to load | Trained on `data/ml/synthetic_transit_data.csv`, which has a `crowd_level` target |
| ETA | Still mock | The supplied `ml_test.py` training script expects `eta_minutes`/`delay_minutes` columns that **do not exist** in the supplied dataset - only `crowd_level` does. Nothing was trained for ETA/delay; wiring these up needs a dataset that actually has those targets. |
| Delay | Still mock | Same reason as ETA. |

## Data: synthetic, not real Delhi transit data

`data/ml/synthetic_transit_data.csv` (6,000 rows) is **synthetic/rule-generated demo data**, not real-world ridership data:

- `is_weekend` and `is_rush_hour` are exact deterministic functions of `day_of_week`/`time_of_day` (100% match on recomputation) - a real dataset wouldn't line up this cleanly.
- `crowd_level` correlates at **0.90** with `is_rush_hour` alone and **0.83** with `traffic_level` - consistent with a formula-driven label, not observed passenger counts.
- No missing values, no duplicate rows, and every categorical column (`traffic_level` 0-10, `weather_level` 0-5, `day_of_week` 0-6) is a suspiciously clean uniform-ish integer range.

Treat all crowd predictions as **demo-quality**, not a validated real-world model. Good enough for a hackathon demo; not a claim about actual Delhi transit crowding.

## Feature schema

Single source of truth: `backend/app/ml/features.py`. The model was trained on (and expects, in this exact order - verified against `model.feature_names_in_`):

```
distance_km, time_of_day, day_of_week, traffic_level, weather_level, current_delay, is_weekend, is_rush_hour
```

`is_weekend`/`is_rush_hour` are derived, not raw inputs - `app/ml/features.py` has the exact formulas (`is_weekend = day_of_week in {5,6}`, `is_rush_hour = 8<=hour<=10 or 17<=hour<=20`).

## Known integration gap (for whoever owns the API/request layer)

The current `/api/recommend` request (`RecommendRequest`) only carries `from`, `to`, `departure_time` (HH:MM, no date). It has no `distance_km`, `traffic_level`, `weather_level`, `current_delay`, or a real calendar date. `PredictionService.predict_crowding` accepts all of these as **optional keyword args** and falls back to dataset-median defaults for anything not supplied, so today's calls run mostly on defaults for those fields (only `time_of_day` from `departure_time`, and `day_of_week` from the server's current date, are real per-request signal right now).

If you want tighter predictions, the two highest-value things to pass through would be `distance_km` (`RoutingService`/`CandidateRoute` already has trip length info) and a real request date. I didn't add these to `RecommendationService`/the API schema myself since that's outside the ML/prediction ownership boundary for this change - flagging it here per the "stop and explain" rule instead.

## Model compatibility

`crowd_model.pkl` was trained under scikit-learn **1.7.2**. Loading it under 1.8.0 works but prints `InconsistentVersionWarning`; `backend/requirements.txt` now pins `scikit-learn==1.7.2` so a fresh install matches exactly and the warning goes away. If you ever need a newer sklearn, retrain first (`python ml/train_crowd_model.py`) and bump the pin at the same time.

## Retraining

```bash
python ml/train_crowd_model.py
```

Reads `data/ml/synthetic_transit_data.csv`, trains, writes `backend/app/ml/artifacts/crowd_model.pkl`. Imports the feature schema from `backend/app/ml/features.py` (not redefined here) so training and serving can't drift apart.

## Files not carried into the backend, and why

The following files were supplied for this integration but are **not** part of the final backend code (only used to inform the above):

- `ml_test.py` - trains ETA/delay models against columns that aren't in the supplied CSV; doesn't run against the actual data as-is.
- `route_crowd_planner.py` - a standalone script that calls the Google Routes API directly and `print()`s results. Its feature-building logic (`step_features`) was extracted into `app/ml/features.py`; the HTTP-calling and printing parts weren't, since prediction unit tests must run with no network access and the prediction layer must not own HTTP/printing (see architecture note in `docs/architecture.md`).
- `trafffic_level.py` - output-formatting helper for the same Google Routes API response shape (hardcodes Bengaluru addresses as a demo). Not ML logic; nothing here was reusable for the prediction layer itself.
