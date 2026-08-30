from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_recommend_success():
    payload = {
        "from": "Kashmere Gate",
        "to": "Rajiv Chowk",
        "departure_time": "09:15",
    }
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "recommended_route" in data
    assert "alternatives" in data
    assert "metadata" in data

    rec = data["recommended_route"]
    assert rec["eta_minutes"] > 0
    assert rec["crowd_score"] >= 0
    assert rec["crowd_level"] in ["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
    assert len(rec["legs"]) > 0
    assert "ML Recommended" in rec["reason"]


def test_recommend_same_origin_destination():
    payload = {
        "from": "Kashmere Gate",
        "to": "Kashmere Gate",
        "departure_time": "09:15",
    }
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 404


def test_recommend_invalid_time_format():
    payload = {
        "from": "Kashmere Gate",
        "to": "Rajiv Chowk",
        "departure_time": "25:70",
    }
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 422


def test_routes_list_endpoint():
    response = client.get("/api/routes?from=Inderlok&to=Dilshad Garden&departure_time=08:30")
    assert response.status_code == 200
    data = response.json()
    assert len(data["routes"]) > 0


def test_stops_search_endpoint():
    response = client.get("/api/stops/search?q=Kashmere&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "stops" in data
    assert len(data["stops"]) > 0
