# Technical Architecture

```text
GTFS / Realtime / Traffic / Weather / Historical Data
                         ↓
                Data Processing Layer
                         ↓
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
        ETA          Crowding       Delay Risk
          └──────────────┼──────────────┘
                         ↓
                 Route Scoring Engine
                         ↓
             ┌───────────┴───────────┐
             ↓                       ↓
        Commuter Output       Government Insights
```

Core route factors:
- Predicted journey time / ETA
- Number of transfers
- Crowding level
- Delay risk

Model health:
- HIGH / MEDIUM / LOW
- Confidence should reflect prediction/data reliability, not be presented as guaranteed accuracy.
