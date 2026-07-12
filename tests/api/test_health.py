from fastapi.testclient import TestClient

from main import app


def test_health() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_routes_are_not_registered() -> None:
    response = TestClient(app).post("/api/auth/register")

    assert response.status_code == 404
