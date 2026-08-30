# TransitAI — Smart Public Transport Intelligence

**Smart India Hackathon (SIH 2026)**

TransitAI is an intelligent multi-modal transit recommendation and network operations intelligence system. It ingests GTFS schedule networks (Delhi Bus & Metro), integrates real-time weather and traffic telemetry, runs machine learning models for ETA regression, delay risk prediction, and crowding level estimation, and provides both a commuter app and a government operations dashboard.

---

## Complete Project Architecture

```text
USER (Commuter or Transport Authority)
 │
 ├── Origin Stop / Current Location
 ├── Destination Stop
 └── Departure Time (24h)
        │
        ▼
   ROUTING ENGINE (GTFS Multi-Modal)
        │
        ├── In-memory spatial index (6,600+ stops, 3,000+ routes)
        ├── Multi-modal graph planner (Bus + Metro + Walking transfers)
        └── Detailed candidate journeys generation
        │
        ▼
 ┌──────────────────────────────────────────┐
 │      DATA & REAL-TIME INFORMATION        │
 ├──────────────────────────────────────────┤
 │ • Delhi DTC Bus & Delhi Metro GTFS data  │
 │ • Open-Meteo live weather telemetry      │
 │ • Real-time traffic congestion factors   │
 │ • Historical ridership curves & headways │
 └──────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────┐
 │                ML ENGINE                 │
 ├──────────────────────────────────────────┤
 │ • ETA Prediction (Ridge Non-Linear Reg)  │
 │ • Delay Prediction & Risk Probability    │
 │ • Crowding Estimation (0-100 score/lvl)  │
 └──────────────────────────────────────────┘
        │
        ▼
    MULTI-OBJECTIVE ROUTE SCORING
        │
        ├── Travel time optimization
        ├── Waiting & transfer penalties
        ├── Predicted delay risk & reliability
        └── Crowding comfort index
        │
        ▼
  RECOMMENDATION & GOVERNMENT INTELLIGENCE
        │
 ┌──────┴───────────────────────────────────┐
 │                                          │
 ▼                                          ▼
PASSENGER COMMUTER UI              GOVERNMENT DASHBOARD
• ★ Recommended / Optimum (ML)     • Network stress & bottleneck heatmap
• ⚡ Quickest route                 • 24h demand curves & 60m forecast
• 🌿 Least Crowded (Calm)          • Corridor economics & revenue
• Delay warnings & crowd meters    • AI Policy intervention simulation
• Interactive schematic diagrams   • Real-time anomaly alert queue
```

---

## Project Structure

```
transit-sih/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── gov.py               # Government analytics & simulation endpoints
│   │   │   ├── health.py            # System health, GTFS & ML metrics
│   │   │   ├── recommendations.py   # Commuter route recommendation API
│   │   │   └── routes.py            # Route detail & stop autocomplete API
│   │   ├── core/
│   │   │   └── config.py            # Environment configuration
│   │   ├── models/
│   │   │   └── schemas.py           # Pydantic data schemas
│   │   ├── services/
│   │   │   ├── gtfs_loader.py       # GTFS ingestion & spatial indexing
│   │   │   ├── prediction_service.py# ML prediction orchestrator
│   │   │   ├── recommendation_service.py # Route ranking & reasoning
│   │   │   ├── routing_service.py   # Multi-modal journey planner
│   │   │   ├── scoring_service.py   # Multi-objective Pareto scoring
│   │   │   ├── traffic_service.py   # Traffic congestion modeling
│   │   │   └── weather_service.py   # Open-Meteo live weather API
│   │   └── main.py                  # FastAPI application entrypoint
│   ├── tests/                       # Pytest test suite (100% passing)
│   └── requirements.txt
├── ml/
│   ├── models/
│   │   └── transit_models.json      # Serialized trained ML model parameters
│   ├── train_models.py              # ML model training pipeline
│   └── inference.py                 # Production ML inference engine
├── frontend/                        # Commuter UI (Vite + React + Lucide)
├── govtdash/                        # Transport Authority Dashboard (Vite + React)
└── data/
    └── processed/
        ├── dtc_gtfs/                # Cleaned Delhi DTC Bus GTFS data
        └── gtfs_metro/              # Cleaned Delhi Metro GTFS data
```

---

## Quick Start Guide

### 1. Train Machine Learning Models
```bash
python ml/train_models.py
```

### 2. Start the Backend API Server
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
API Documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 3. Run Automated Tests
```bash
pytest backend/tests
```

### 4. Start the Commuter Passenger App
```bash
cd frontend
npm install
npm run dev
```

### 5. Start the Government Dashboard
```bash
cd govtdash
npm install
npm run dev
```

---

## API Endpoints Reference

### Commuter APIs
- `POST /api/recommend` — Recommends best journey with alternatives, ETA, delay, crowd levels, and ML explanations.
- `GET /api/stops/search?q={query}&limit=8` — Real-time stop autocomplete search.
- `GET /api/routes?from={from}&to={to}&departure_time={time}` — Lists candidate routes with scores.
- `GET /api/health` — System health, indexed stop counts, and ML model status.

### Government Operations APIs
- `GET /api/gov/overview` — Network load, delay hotspots, high-demand corridors, active fleet count.
- `GET /api/gov/corridors` — Corridor-by-corridor demand, delay, crowding, and financials.
- `GET /api/gov/demand?peak_window=...` — 24h ridership distribution and 60-minute forecast.
- `GET /api/gov/alerts` — Active anomaly alerts and recommended operations.
- `POST /api/gov/simulate-action` — Interactive policy simulation (`frequency`, `deploy_bus`, `reroute`).
