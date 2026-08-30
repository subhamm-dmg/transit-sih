# TransitAI — Smart Public Transport Intelligence

**Smart India Hackathon (SIH 2026)**

TransitAI is an end-to-end intelligent public transport routing and analytics platform. It combines static GTFS schedule feeds (Delhi DTC Bus & Delhi Metro), real-time weather and traffic telemetry, and Machine Learning models (ETA regression, delay risk prediction, and crowding estimation) to deliver commuter route recommendations and government network intelligence.

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
        └── Accurate mode-diverse journey generation
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
• Mode diversity (Metro vs Bus)    • AI Policy intervention simulation
• Interactive schematic diagrams   • Real-time anomaly alert queue
```

---

## Project Structure

```text
transit-sih/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── gov.py               # Government analytics & simulation endpoints
│   │   │   ├── health.py            # System health, GTFS & ML metrics
│   │   │   ├── insights.py          # Transit insights endpoints
│   │   │   ├── recommendations.py   # Commuter route recommendation API
│   │   │   └── routes.py            # Route detail & stop autocomplete API
│   │   ├── core/
│   │   │   └── config.py            # Environment configuration
│   │   ├── ml/                      # ML feature extraction & loaders
│   │   ├── models/
│   │   │   ├── schemas.py           # Pydantic data schemas
│   │   │   └── insights_schemas.py  # Insights data models
│   │   ├── services/
│   │   │   ├── analytics_service.py # Corridor analytics & demand service
│   │   │   ├── gov_service.py       # Government simulation service
│   │   │   ├── gtfs_loader.py       # GTFS ingestion & spatial indexing
│   │   │   ├── gtfs_service.py      # GTFS feed reader & queries
│   │   │   ├── prediction_service.py# ML prediction orchestrator
│   │   │   ├── recommendation_service.py # Route ranking & reasoning
│   │   │   ├── routing_service.py   # Multi-modal journey planner
│   │   │   ├── scoring_service.py   # Multi-objective Pareto scoring
│   │   │   ├── traffic_service.py   # Traffic congestion modeling
│   │   │   └── weather_service.py   # Open-Meteo live weather API
│   │   └── main.py                  # FastAPI application entrypoint
│   ├── tests/                       # Pytest test suite (29 tests passing)
│   └── requirements.txt
├── ml/
│   ├── models/
│   │   └── transit_models.json      # Serialized trained ML model parameters
│   ├── train_models.py              # ML model training pipeline
│   ├── train_crowd_model.py         # Crowd estimation training pipeline
│   └── inference.py                 # Production ML inference engine
├── frontend/                        # Commuter UI (Vite + React + Lucide + Google Maps)
├── govtdash/                        # Transport Authority Dashboard (Vite + React)
└── data/
    └── processed/
        ├── dtc_gtfs/                # Cleaned Delhi DTC Bus GTFS data
        └── gtfs_metro/              # Cleaned Delhi Metro GTFS data
```

---

## Step-by-Step Setup & How to Run

### Prerequisites
- **Python 3.9+** (with `pip`)
- **Node.js 18+** (with `npm`)
- **Git**

---

### Step 1: Install Backend Dependencies & Run Backend Server

Open a terminal in the project root:

```bash
# 1. Navigate to backend directory
cd backend

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Start the FastAPI backend server
python -m uvicorn app.main:app --reload --port 8000
```

> **Backend is running at:** [http://localhost:8000](http://localhost:8000)  
> **Interactive Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)  
> **Health check endpoint:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Step 2: Start the Commuter Passenger App (Frontend)

Open a **new terminal window**:

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install Node dependencies
npm install

# 3. (Optional) Set up Google Maps API Key in .env.local
# Create a .env.local file:
# VITE_GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
# (If omitted, the app automatically falls back to the built-in interactive SVG schematic map)

# 4. Start the Vite development server
npm run dev
```

> **Commuter App is open at:** [http://localhost:5173](http://localhost:5173)

#### How to use the Commuter App:
1. Open [http://localhost:5173](http://localhost:5173) in your browser.
2. Select or search an **Origin** (e.g. `Kashmere Gate` or `Rajiv Chowk`).
3. Select or search a **Destination** (e.g. `Central Secretariat`, `Hauz Khas`, `Dilshad Garden`, or `Noida Sector 18`).
4. Set the **Departure Time** (defaults to current time).
5. Click **"Find routes"**.
6. View the mode-diverse journey options:
   - If only one direct connection exists (e.g. direct Metro), it displays **only that direct route**.
   - If multiple modes are available, it displays distinct **Metro**, **Bus**, and **Multi-Modal** options with predicted ETA, delay risk badges, crowding meters, and ML explanations.

---

### Step 3: Start the Government Transport Dashboard

Open another **new terminal window**:

```bash
# 1. Navigate to govtdash directory
cd govtdash

# 2. Install Node dependencies
npm install

# 3. Start the Vite development server
npm run dev -- --port 5174
```

> **Government Dashboard is open at:** [http://localhost:5174](http://localhost:5174)

#### How to use the Government Dashboard:
1. Open [http://localhost:5174](http://localhost:5174) in your browser.
2. **Overview**: View city-wide network load, delay hotspots, high-demand corridors, and fleet status.
3. **Corridor Analysis**: Click **"Analyse network"** to inspect corridor-by-corridor demand, stop crowding, and financial economics.
4. **Policy Interventions**: Click **"Test policy interventions"** and click **"Run"** on actions (e.g. *Increase bus frequency*, *Deploy extra buses*, *Passenger rerouting*) to simulate real-time load and delay reduction impact.
5. **Demand & Alerts**: Explore 24-hour passenger volume distribution and real-time operational alert queues.

---

### Step 4: Run Automated Tests

To verify that all backend routing, ML prediction, scoring, and government APIs are working properly:

```bash
# From project root
python -m pytest backend/tests
```

All 29 tests will execute and validate the complete service stack.

---

### Step 5: (Optional) Retrain Machine Learning Models

To retrain the ML regression and decision ensemble models:

```bash
# From project root
python ml/train_models.py
python ml/train_crowd_model.py
```

---

## API Endpoints Reference

### Commuter APIs
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/recommend` | Multi-modal journey planner with ML ETA, delay, and crowding |
| `GET` | `/api/stops/search?q={query}&limit=8` | Stop autocomplete search across 6,600+ stops |
| `GET` | `/api/routes?from={from}&to={to}` | Candidate routes listing with composite scores |
| `GET` | `/api/health` | Health check reporting indexed GTFS stops, routes, and ML status |

### Government Operations & Insights APIs
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/gov/overview` | Network stress overview, hotspots, and active fleet count |
| `GET` | `/api/gov/corridors` | Corridor-by-corridor demand, delay, crowding, and revenue |
| `GET` | `/api/gov/demand` | 24-hour ridership distribution and 60-minute forecast |
| `GET` | `/api/gov/alerts` | Active anomaly alerts and recommended operations |
| `POST` | `/api/gov/simulate-action` | Interactive policy simulation (`frequency`, `deploy_bus`, `reroute`) |
| `GET` | `/api/insights/summary` | Transport authority network summary |
| `GET` | `/api/insights/bottlenecks` | Choke point and delay bottleneck analytics |

---

## License & Attribution
Developed for **Smart India Hackathon (SIH 2026)**.
Transit data sourced from Open Transit Data (Delhi DTC & DMRC GTFS) and Open-Meteo Weather APIs.
