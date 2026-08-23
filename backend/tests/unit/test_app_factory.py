import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import create_app


def test_create_app_returns_distinct_instances() -> None:
    assert create_app() is not create_app()


def test_health_live_returns_status_live() -> None:
    client = TestClient(create_app())

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_health_live_is_not_mounted_under_api_v1() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/health/live")

    assert response.status_code == 404


def test_create_app_raises_on_invalid_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        create_app()
