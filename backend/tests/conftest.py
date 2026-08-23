import pytest

VALID_ENVIRONMENT: dict[str, str] = {
    "ENVIRONMENT": "test",
    "DATABASE_URL": "postgresql+psycopg://postgres:postgres@localhost:5432/business_management_platform_test",
    "JWT_SECRET": "correct-horse-battery-staple-0123456789",
    "JWT_ISSUER": "business-management-platform",
    "JWT_AUDIENCE": "business-management-platform-api",
    "CORS_ALLOWED_ORIGINS": '["http://localhost:5173"]',
    "LOG_LEVEL": "INFO",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
    "REFRESH_TOKEN_EXPIRE_DAYS": "14",
}


@pytest.fixture(autouse=True)
def valid_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in VALID_ENVIRONMENT.items():
        monkeypatch.setenv(name, value)
