# TransitAI — Smart Public Transport Intelligence

SIH 2026 hackathon project.

## Problem
Predict public-transport journey conditions and recommend better routes using ETA, transfers, crowding and delay risk, while providing transport authorities with actionable network insights.

## MVP
- One major city
- 2–3 route alternatives
- ETA prediction
- Crowding level + confidence
- Delay-risk warning
- Recommended route
- Government-side demand/delay/bottleneck insights

## Architecture
Data Sources → Data Processing → ML Prediction → Route Scoring → User & Government Outputs

## Team Workflow
- `main` = stable/submission branch
- Each member works on their own feature branch
- Open a Pull Request before merging into `main`
- Do not push directly to `main`
- Keep commits small and descriptive

### Branches
- `data/<name>` — data ingestion/cleaning
- `ml/<name>` — ML models/evaluation
- `crowding/<name>` — crowding estimation
- `routing/<name>` — route scoring/optimization
- `frontend/<name>` — UI
- `backend/<name>` — APIs/integration


## Setup
Add project-specific setup instructions here as the stack is finalized.
