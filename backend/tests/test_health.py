"""
Integration tests for the Transit SIH API.

These tests use the real local Delhi DTC GTFS dataset.
No external API or internet connection is required.
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# A real direct DTC connection confirmed in the local GTFS dataset.
ORIGIN = "Narela Terminal"
DESTINATION = "Kashmere Gate"
DEPARTURE_TIME = "08:00"


def test_health_check() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["service"] == "transit-sih-backend"


def test_recommend_success() -> None:
    response = client.post(
        "/api/recommend",
        json={
            "from": ORIGIN,
            "to": DESTINATION,
            "departure_time": DEPARTURE_TIME,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert "recommended_route" in body
    assert "alternatives" in body
    assert "metadata" in body

    recommended = body["recommended_route"]

    assert recommended["route_id"]
    assert recommended["route_name"]
    assert recommended["eta_minutes"] > 0
    assert recommended["waiting_minutes"] >= 0
    assert recommended["delay_minutes"] >= 0
    assert recommended["crowd_level"] in (
        "LOW",
        "MODERATE",
        "HIGH",
        "VERY_HIGH",
    )
    assert 0 <= recommended["crowd_score"] <= 100
    assert 0.0 <= recommended["reliability"] <= 1.0
    assert recommended["transfers"] >= 0

    assert body["metadata"]["prediction_mode"] == "mock"


def test_recommend_unknown_stop_pair_returns_404() -> None:
    """
    Unknown/unconnected stops must not receive fake fallback routes.
    """

    response = client.post(
        "/api/recommend",
        json={
            "from": "Definitely Unknown Stop",
            "to": "Definitely Another Unknown Stop",
            "departure_time": "10:00",
        },
    )

    assert response.status_code == 404

    body = response.json()

    assert body["error"] == "request_error"
    assert "No direct DTC routes found" in body["detail"]


def test_recommend_invalid_departure_time() -> None:
    response = client.post(
        "/api/recommend",
        json={
            "from": ORIGIN,
            "to": DESTINATION,
            "departure_time": "25:99",
        },
    )

    assert response.status_code == 422


def test_recommend_same_origin_and_destination() -> None:
    response = client.post(
        "/api/recommend",
        json={
            "from": ORIGIN,
            "to": ORIGIN,
            "departure_time": "10:00",
        },
    )

    assert response.status_code == 404


def test_get_routes_list() -> None:
    response = client.get(
        "/api/routes",
        params={
            "from": ORIGIN,
            "to": DESTINATION,
            "departure_time": DEPARTURE_TIME,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert "routes" in body
    assert "metadata" in body
    assert len(body["routes"]) >= 1

    route = body["routes"][0]

    assert route["route_id"]
    assert route["route_name"]
    assert route["eta_minutes"] > 0


def test_get_route_detail() -> None:
    list_response = client.get(
        "/api/routes",
        params={
            "from": ORIGIN,
            "to": DESTINATION,
            "departure_time": DEPARTURE_TIME,
        },
    )

    assert list_response.status_code == 200

    route_id = list_response.json()["routes"][0]["route_id"]

    detail_response = client.get(
        f"/api/routes/{route_id}",
        params={
            "from": ORIGIN,
            "to": DESTINATION,
            "departure_time": DEPARTURE_TIME,
        },
    )

    assert detail_response.status_code == 200
    assert detail_response.json()["route_id"] == route_id


def test_get_route_detail_not_found() -> None:
    response = client.get(
        "/api/routes/NOPE",
        params={
            "from": ORIGIN,
            "to": DESTINATION,
            "departure_time": DEPARTURE_TIME,
        },
    )

    assert response.status_code == 404
