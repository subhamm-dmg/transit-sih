from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_insights_summary() -> None:
    response = client.get("/api/insights/summary")

    assert response.status_code == 200
    body = response.json()

    assert body["dtc"]["available"] is True
    assert body["dtc"]["stop_count"] > 0


def test_insights_demand() -> None:
    response = client.get("/api/insights/demand")

    assert response.status_code == 200

    body = response.json()
    assert body["datasets"]


def test_insights_delays() -> None:
    response = client.get("/api/insights/delays")

    assert response.status_code == 200

    body = response.json()
    assert body["delay_data_available"] is False


def test_insights_crowding() -> None:
    response = client.get("/api/insights/crowding")

    assert response.status_code == 200

    body = response.json()
    assert body["datasets"]


def test_insights_bottlenecks() -> None:
    response = client.get("/api/insights/bottlenecks")

    assert response.status_code == 200

    body = response.json()
    assert body["datasets"]


def test_existing_health_and_recommendation_routes_still_exist() -> None:
    health = client.get("/api/health")
    assert health.status_code == 200

    recommendation = client.post(
        "/api/recommend",
        json={
            "from": "Narela Terminal",
            "to": "Kashmere Gate",
            "departure_time": "08:00",
        },
    )

    assert recommendation.status_code == 200
    assert "recommended_route" in recommendation.json()
