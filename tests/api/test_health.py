from fastapi.testclient import TestClient

from main import app


def test_health() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_routes_are_not_registered() -> None:
    response = TestClient(app).post("/api/auth/register")

    assert response.status_code == 404


def test_application_does_not_add_cors_headers() -> None:
    response = TestClient(app).get("/health", headers={"Origin": "https://frontend.example"})

    assert "access-control-allow-origin" not in response.headers
    assert "access-control-allow-credentials" not in response.headers
