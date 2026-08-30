# Transit SIH — Backend (MVP)

FastAPI backend for the Transit SIH hackathon project. Runs **fully
offline** tonight using deterministic mock adapters for routing,
predictions, traffic, and weather — no database, no API keys, no
internet required.

## Setup

### 1. Create a virtual environment

Windows:
```
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:
```
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. (Optional) configure environment

```
cp .env.example .env
```

The app runs fine with no `.env` file at all — every setting has a safe
default.

### 4. Run the server

```
uvicorn app.main:app --reload --port 8000
```

The API will be live at `http://localhost:8000`, with interactive docs
at `http://localhost:8000/docs`.

### 5. Run tests

```
pytest
```

## Architecture

```
HTTP request
    -> API endpoint (app/api/)
    -> Service (app/services/)
    -> Routing / Prediction / Traffic / Weather (mock adapters)
    -> Pydantic response schema (app/models/schemas.py)
```

Business logic lives in `app/services/`, never in the route handlers
themselves. `RecommendationService` orchestrates
`RoutingService` + `PredictionService` + scoring, and both `/api/routes`
and `/api/recommend` reuse it.

Every mock adapter (`RoutingService`, `PredictionService`,
`TrafficService`, `WeatherService`) is written to be swapped for a real
implementation later **without changing the API contract**:

| Service | Tonight | Tomorrow |
|---|---|---|
| RoutingService | Small hardcoded stop/route network | GTFS-based routing |
| PredictionService | Deterministic mock ETA/delay/crowding | Real ML models |
| TrafficService | Deterministic mock traffic level | Real traffic API |
| WeatherService | Deterministic mock weather | Open-Meteo or similar |

## API Endpoints

### `GET /api/health`

```
curl http://localhost:8000/api/health
```

```json
{ "status": "ok", "service": "transit-sih-backend" }
```

### `POST /api/recommend`

```
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"from": "Majestic", "to": "Indiranagar", "departure_time": "18:00"}'
```

```json
{
  "recommended_route": {
    "route_id": "R3",
    "route_name": "Metro + Walk",
    "eta_minutes": 27,
    "waiting_minutes": 6,
    "delay_minutes": 4,
    "crowd_level": "MODERATE",
    "crowd_score": 45,
    "reliability": 0.83,
    "transfers": 0,
    "reason": "Best balance of travel time, low crowding (MODERATE), and delay risk",
    "score": 51.2
  },
  "alternatives": [ /* ... */ ],
  "metadata": {
    "prediction_mode": "mock",
    "data_source": "mock",
    "confidence": 0.75
  }
}
```

### `GET /api/routes`

```
curl "http://localhost:8000/api/routes?from=Majestic&to=Indiranagar&departure_time=18:00"
```

Returns all candidate routes (same shape as one route object above),
ranked best-first.

### `GET /api/routes/{route_id}`

```
curl "http://localhost:8000/api/routes/R2?from=Majestic&to=Indiranagar&departure_time=18:00"
```

Returns details for a single route.

## Error handling

- Invalid request body / query params -> `422` with `{"error": "...", "detail": "..."}`
- Invalid `departure_time` (not `HH:MM`, 24h) -> `422`
- Same origin and destination, or no route found -> `404`
- Unexpected server error -> `500` (generic message, no internals leaked)

## Notes

- `route_id` values (`R1`, `R2`, ...) are only guaranteed stable within
  a single request/response — they're generated fresh per query against
  the mock network, not persisted IDs.
- The mock transit network only has a real entry for
  `Majestic -> Indiranagar`; any other stop pair falls back to a generic
  two-route network so the demo never dead-ends on unfamiliar stop
  names typed at judging time.
