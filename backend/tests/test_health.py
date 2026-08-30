"""
Basic tests for /api/health and /api/recommend.

These run fully offline - no external API keys, no internet, no
database. Uses FastAPI's TestClient (sync, based on httpx).
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "transit-sih-backend"


def test_recommend_success() -> None:
    response = client.post(
        "/api/recommend",
        json={"from": "Majestic", "to": "Indiranagar", "departure_time": "18:00"},
    )
    assert response.status_code == 200
    body = response.json()

    assert "recommended_route" in body
    assert "alternatives" in body
    assert "metadata" in body

    recommended = body["recommended_route"]
    assert recommended["route_id"]
    assert recommended["eta_minutes"] > 0
    assert recommended["crowd_level"] in ("LOW", "MODERATE", "HIGH", "VERY_HIGH")
    assert 0.0 <= recommended["reliability"] <= 1.0

    assert body["metadata"]["prediction_mode"] == "heuristic"


def test_recommend_unknown_stop_pair_falls_back() -> None:
    # Unknown stop pairs should still return a result via the fallback
    # mock network, not an error - keeps the demo resilient to any judge
    # typing arbitrary stop names.
    response = client.post(
        "/api/recommend",
        json={"from": "Some Stop", "to": "Another Stop", "departure_time": "10:00"},
    )
    assert response.status_code == 200


def test_recommend_invalid_departure_time() -> None:
    response = client.post(
        "/api/recommend",
        json={"from": "Majestic", "to": "Indiranagar", "departure_time": "25:99"},
    )
    assert response.status_code == 422


def test_recommend_same_origin_and_destination() -> None:
    response = client.post(
        "/api/recommend",
        json={"from": "Majestic", "to": "Majestic", "departure_time": "10:00"},
    )
    assert response.status_code == 404


def test_get_routes_list() -> None:
    response = client.get(
        "/api/routes",
        params={"from": "Majestic", "to": "Indiranagar", "departure_time": "18:00"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["routes"]) >= 1


def test_get_route_detail() -> None:
    list_response = client.get(
        "/api/routes",
        params={"from": "Majestic", "to": "Indiranagar", "departure_time": "18:00"},
    )
    route_id = list_response.json()["routes"][0]["route_id"]

    detail_response = client.get(
        f"/api/routes/{route_id}",
        params={"from": "Majestic", "to": "Indiranagar", "departure_time": "18:00"},
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["route_id"] == route_id


def test_get_route_detail_not_found() -> None:
    response = client.get(
        "/api/routes/NOPE",
        params={"from": "Majestic", "to": "Indiranagar", "departure_time": "18:00"},
    )
    assert response.status_code == 404
