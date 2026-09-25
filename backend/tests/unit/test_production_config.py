"""Red/Green contracts for the production configuration safety decision."""

import json
from typing import NamedTuple
from urllib.parse import quote

import pytest

from app.core import config
from app.core.config import Settings
from tests.conftest import VALID_JWT_SECRET

SAFE_PASSWORD_PARTS = ("production", "safe", "fixture", "value")
SAFE_PASSWORD = "-".join(SAFE_PASSWORD_PARTS)
SAFE_DATABASE_URL = f"postgresql+psycopg://app:{SAFE_PASSWORD}@db.example/appdb"
SAFE_ORIGINS = '["https://app.example.com"]'

MISSING_PASSWORD = "DATABASE_URL must include a password in production"
DEFAULT_PASSWORD = "DATABASE_URL password must not be a default value or the username in production"
PLACEHOLDER_PASSWORD = "DATABASE_URL password must not contain a placeholder marker in production"
SHORT_PASSWORD = "DATABASE_URL password must be at least 16 characters in production"
QUERY_PASSWORD = "DATABASE_URL must not carry a password query parameter in production"
DEBUG_LOG = "LOG_LEVEL must not be DEBUG in production"
HTTP_ORIGIN = "CORS_ALLOWED_ORIGINS must use https in production"
LOCAL_ORIGIN = "CORS_ALLOWED_ORIGINS must not use a loopback or unspecified host in production"


class ProductionCase(NamedTuple):
    name: str
    setting: str
    value: str
    message: str
    sensitive: str


CASES = [
    ProductionCase(
        "missing-password",
        "DATABASE_URL",
        "postgresql+psycopg://app@db.example/appdb",
        MISSING_PASSWORD,
        "app@db.example",
    ),
    ProductionCase(
        "empty-password",
        "DATABASE_URL",
        "postgresql+psycopg://app:@db.example/appdb",
        MISSING_PASSWORD,
        "app:@db.example",
    ),
    ProductionCase(
        "fifteen-characters",
        "DATABASE_URL",
        "postgresql+psycopg://app:Ab3Def5Gh7Jk9Lm@db.example/appdb",
        SHORT_PASSWORD,
        "Ab3Def5Gh7Jk9Lm",
    ),
    ProductionCase(
        "fifteen-multibyte-characters",
        "DATABASE_URL",
        f"postgresql+psycopg://app:{quote('é' * 15)}@db.example/appdb",
        SHORT_PASSWORD,
        "é" * 15,
    ),
    ProductionCase(
        "fifteen-percent-decoded-characters",
        "DATABASE_URL",
        f"postgresql+psycopg://app:{'%41' * 15}@db.example/appdb",
        SHORT_PASSWORD,
        "%41" * 15,
    ),
    ProductionCase(
        "postgres-default",
        "DATABASE_URL",
        "postgresql+psycopg://app:postgres@db.example/appdb",
        DEFAULT_PASSWORD,
        "postgres",
    ),
    ProductionCase(
        "password-default-case-insensitive",
        "DATABASE_URL",
        "postgresql+psycopg://app:PASSWORD@db.example/appdb",
        DEFAULT_PASSWORD,
        "PASSWORD",
    ),
    ProductionCase(
        "username-equality-case-insensitive",
        "DATABASE_URL",
        "postgresql+psycopg://APP:app@db.example/appdb",
        DEFAULT_PASSWORD,
        "APP:app",
    ),
    ProductionCase(
        "placeholder-marker-case-insensitive",
        "DATABASE_URL",
        "postgresql+psycopg://app:prefixChangeMeSuffix0123456789@db.example/appdb",
        PLACEHOLDER_PASSWORD,
        "prefixChangeMeSuffix0123456789",
    ),
    ProductionCase(
        "password-query-key",
        "DATABASE_URL",
        f"{SAFE_DATABASE_URL}?password=x",
        QUERY_PASSWORD,
        "password=x",
    ),
    ProductionCase(
        "encoded-password-query-key",
        "DATABASE_URL",
        f"{SAFE_DATABASE_URL}?pass%77ord=x",
        QUERY_PASSWORD,
        "pass%77ord=x",
    ),
    ProductionCase("debug-log-level", "LOG_LEVEL", "debug", DEBUG_LOG, "debug"),
    ProductionCase(
        "http-origin",
        "CORS_ALLOWED_ORIGINS",
        '["http://app.example.com"]',
        HTTP_ORIGIN,
        "http://app.example.com",
    ),
    ProductionCase(
        "password-query-key-trailing-space",
        "DATABASE_URL",
        f"{SAFE_DATABASE_URL}?password%20=postgres",
        QUERY_PASSWORD,
        "password%20=postgres",
    ),
    ProductionCase(
        "password-query-key-leading-space",
        "DATABASE_URL",
        f"{SAFE_DATABASE_URL}?%20password=postgres",
        QUERY_PASSWORD,
        "%20password=postgres",
    ),
    ProductionCase(
        "password-query-key-after-embedded-pair",
        "DATABASE_URL",
        f"{SAFE_DATABASE_URL}?sslmode%3Dprefer%20password=postgres",
        QUERY_PASSWORD,
        "sslmode%3Dprefer%20password=postgres",
    ),
    ProductionCase(
        "uppercase-password-query-key",
        "DATABASE_URL",
        f"{SAFE_DATABASE_URL}?PASSWORD=x",
        QUERY_PASSWORD,
        "PASSWORD=x",
    ),
    ProductionCase(
        "mixed-origins-loopback",
        "CORS_ALLOWED_ORIGINS",
        '["https://app.example.com", "https://localhost"]',
        LOCAL_ORIGIN,
        "https://localhost",
    ),
    ProductionCase(
        "mixed-origins-http",
        "CORS_ALLOWED_ORIGINS",
        '["https://app.example.com", "http://api.example.com"]',
        HTTP_ORIGIN,
        "http://api.example.com",
    ),
    ProductionCase(
        "password-query-key-after-quoted-value",
        "DATABASE_URL",
        f"{SAFE_DATABASE_URL}?application_name%3D%27x%27password=postgres",
        QUERY_PASSWORD,
        "application_name%3D%27x%27password=postgres",
    ),
    ProductionCase(
        "password-query-key-with-embedded-equals",
        "DATABASE_URL",
        f"{SAFE_DATABASE_URL}?password%3Dpostgres%20sslmode=prefer",
        QUERY_PASSWORD,
        "password%3Dpostgres%20sslmode=prefer",
    ),
]

for name, host in (
    ("localhost", "localhost"),
    ("uppercase-localhost-trailing-dot", "LOCALHOST."),
    ("localhost-subdomain", "app.localhost"),
    ("ipv4-loopback", "127.0.0.2"),
    ("ipv4-short-loopback", "127.1"),
    ("ipv4-short-unspecified", "0"),
    ("ipv4-unspecified", "0.0.0.0"),
    ("ipv6-loopback", "[::1]"),
    ("ipv6-expanded-loopback-port", "[0:0:0:0:0:0:0:1]:8443"),
    ("ipv6-unspecified", "[::]"),
    ("ipv4-mapped-ipv6-loopback", "[::ffff:127.0.0.1]"),
):
    CASES.append(
        ProductionCase(
            name,
            "CORS_ALLOWED_ORIGINS",
            json.dumps([f"https://{host}"]),
            LOCAL_ORIGIN,
            host,
        )
    )


def _set_safe_environment(monkeypatch: pytest.MonkeyPatch, environment: str) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("DATABASE_URL", SAFE_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)
    monkeypatch.setenv("JWT_ISSUER", "business-management-platform")
    monkeypatch.setenv("JWT_AUDIENCE", "business-management-platform-api")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", SAFE_ORIGINS)
    monkeypatch.setenv("LOG_LEVEL", "INFO")


@pytest.mark.unit
@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_production_rejects_unsafe_setting_with_fixed_confidential_message(
    monkeypatch: pytest.MonkeyPatch, case: ProductionCase
) -> None:
    _set_safe_environment(monkeypatch, "production")
    monkeypatch.setenv(case.setting, case.value)

    with pytest.raises(config.ConfigurationError) as raised:
        config.load_settings()

    error = raised.value
    assert error.errors() == [{"loc": (), "msg": f"Value error, {case.message}"}]
    assert error.__cause__ is None
    assert error.__context__ is None
    for diagnostic in (str(error), str(error.errors()), error.json()):
        assert case.sensitive not in diagnostic
        assert case.value not in diagnostic


@pytest.mark.unit
@pytest.mark.parametrize(
    "password",
    ["A1b2C3d4E5f6G7h8", "é" * 16],
    ids=["sixteen-ascii-characters", "sixteen-multibyte-characters"],
)
def test_production_accepts_safe_passwords(monkeypatch: pytest.MonkeyPatch, password: str) -> None:
    _set_safe_environment(monkeypatch, "production")
    monkeypatch.setenv(
        "DATABASE_URL", f"postgresql+psycopg://app:{quote(password)}@db.example/appdb"
    )

    settings = Settings()

    assert settings.environment == "production"
    assert settings.log_level == "INFO"
    assert settings.cors_allowed_origins == ["https://app.example.com"]


@pytest.mark.unit
@pytest.mark.parametrize("environment", ["development", "test"])
@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_nonproduction_accepts_each_production_only_case(
    monkeypatch: pytest.MonkeyPatch, environment: str, case: ProductionCase
) -> None:
    _set_safe_environment(monkeypatch, environment)
    monkeypatch.setenv(case.setting, case.value)

    settings = Settings()

    assert settings.environment == environment


@pytest.mark.unit
def test_database_url_is_redacted_from_settings_representations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canary = "R1DbCanaryA9v8U7t6W5x4"
    _set_safe_environment(monkeypatch, "production")
    monkeypatch.setenv("DATABASE_URL", f"postgresql+psycopg://app:{canary}@db.example/appdb")

    settings = Settings()

    for representation in (
        repr(settings),
        str(settings),
        repr(settings.model_dump()),
        settings.model_dump_json(),
    ):
        assert canary not in representation


@pytest.mark.unit
def test_non_utf8_jwt_secret_has_only_fixed_confidential_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surrogate = "\udcff"
    _set_safe_environment(monkeypatch, "test")
    monkeypatch.setenv("JWT_SECRET", surrogate)

    with pytest.raises(config.ConfigurationError) as raised:
        config.load_settings()

    error = raised.value
    assert error.errors() == [
        {"loc": ("jwt_secret",), "msg": "Value error, JWT_SECRET must be valid UTF-8"}
    ]
    assert error.__cause__ is None
    assert error.__context__ is None
    for diagnostic in (str(error), str(error.errors()), error.json()):
        assert surrogate not in diagnostic
        assert r"\udcff" not in diagnostic
