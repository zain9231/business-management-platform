import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import config
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

    with pytest.raises(ValueError) as raised:
        create_app()

    assert isinstance(raised.value, config.ConfigurationError)


@pytest.mark.parametrize(
    ("name", "value", "secret"),
    [
        ("JWT_SECRET", "audit-short-secret", "audit-short-secret"),
        (
            "DATABASE_URL",
            "mysql://audit:audit-db-secret@localhost/db",
            "audit-db-secret",
        ),
        (
            "CORS_ALLOWED_ORIGINS",
            '["https://audit:audit-cors-secret@example.com"]',
            "audit-cors-secret",
        ),
    ],
)
def test_uvicorn_startup_fails_without_logging_configuration_secrets(
    name: str,
    value: str,
    secret: str,
) -> None:
    environment = os.environ.copy()
    environment[name] = value
    result = subprocess.run(
        [sys.executable, "-m", "uvicorn", "app.main:create_app", "--factory"],
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode != 0
    assert "ConfigurationError" in result.stderr
    assert name.lower() in result.stderr
    assert secret not in result.stdout + result.stderr
