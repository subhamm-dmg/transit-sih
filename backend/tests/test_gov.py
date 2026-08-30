from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_gov_overview():
    response = client.get("/api/gov/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["delay_hotspots"] > 0
    assert data["network_load_pct"] > 0


def test_gov_corridors():
    response = client.get("/api/gov/corridors")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3
    assert data[0]["id"] == "R9"


def test_gov_demand():
    response = client.get("/api/gov/demand?peak_window=08:00 – 10:00 AM")
    assert response.status_code == 200
    data = response.json()
    assert len(data["hourly_distribution"]) == 15


def test_gov_alerts():
    response = client.get("/api/gov/alerts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0


def test_gov_simulation():
    payload = {"action_type": "deploy_bus", "corridor_id": "R9"}
    response = client.post("/api/gov/simulate-action", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["after_delay"] <= data["before_delay"]
    assert data["roi_score"] > 0
