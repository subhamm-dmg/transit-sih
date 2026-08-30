from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "transit-sih-backend"
    assert "stops_indexed" in data
    assert "routes_indexed" in data
    assert data["ml_models_loaded"] is True
