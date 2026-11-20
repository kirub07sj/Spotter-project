from rest_framework.test import APIClient


def test_health_returns_ok_and_version() -> None:
    response = APIClient().get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["version"], str) and body["version"]
