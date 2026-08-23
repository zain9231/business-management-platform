import pytest
from pydantic import SecretStr, ValidationError
from pydantic_settings import SettingsError

from app.core.config import JWT_SECRET_SENTINEL, Settings

REQUIRED_NO_DEFAULT_VARS = [
    "DATABASE_URL",
    "JWT_SECRET",
    "JWT_ISSUER",
    "JWT_AUDIENCE",
    "CORS_ALLOWED_ORIGINS",
]

ENVIRONMENTS = ["development", "test", "production"]

PLACEHOLDER_MARKERS = [
    "placeholder",
    "change-me",
    "change_me",
    "changeme",
    "replace-me",
    "replace_me",
    "your-secret",
    "your_secret",
    "example-secret",
    "example_secret",
]

ENV_EXAMPLE_SENTINEL = "replace-me-with-at-least-32-random-bytes"

VALID_SECRET = "correct-horse-battery-staple-0123456789"


@pytest.mark.parametrize("missing_var", REQUIRED_NO_DEFAULT_VARS)
@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_missing_required_variable_raises(
    monkeypatch: pytest.MonkeyPatch, environment: str, missing_var: str
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.delenv(missing_var, raising=False)

    with pytest.raises(ValidationError):
        Settings()


def test_short_jwt_secret_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "too-short")

    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("marker", PLACEHOLDER_MARKERS)
def test_jwt_secret_rejects_each_placeholder_marker(
    monkeypatch: pytest.MonkeyPatch, marker: str
) -> None:
    padded_secret = f"{marker}-0123456789012345678901234567890123456789"
    monkeypatch.setenv("JWT_SECRET", padded_secret)

    with pytest.raises(ValidationError):
        Settings()


def test_jwt_secret_sentinel_constant_has_approved_value() -> None:
    assert JWT_SECRET_SENTINEL == "replace-me-with-at-least-32-random-bytes"


def test_jwt_secret_rejects_env_example_sentinel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", ENV_EXAMPLE_SENTINEL)

    with pytest.raises(ValidationError):
        Settings()


def test_jwt_secret_marker_matching_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    padded_secret = "CHANGE-ME-0123456789012345678901234567890123456789"
    monkeypatch.setenv("JWT_SECRET", padded_secret)

    with pytest.raises(ValidationError):
        Settings()


def test_jwt_secret_marker_matching_ignores_surrounding_whitespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    padded_secret = "   changeme-0123456789012345678901234567890123456789   "
    monkeypatch.setenv("JWT_SECRET", padded_secret)

    with pytest.raises(ValidationError):
        Settings()


def test_jwt_secret_rejects_30_utf8_byte_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "é" * 15)

    with pytest.raises(ValidationError):
        Settings()


def test_jwt_secret_accepts_32_utf8_byte_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "é" * 16
    monkeypatch.setenv("JWT_SECRET", secret)

    settings = Settings()

    assert settings.jwt_secret.get_secret_value() == secret


def test_jwt_secret_field_is_secret_str() -> None:
    settings = Settings()

    assert isinstance(settings.jwt_secret, SecretStr)


def test_jwt_secret_str_and_repr_do_not_expose_value() -> None:
    settings = Settings()

    assert VALID_SECRET not in str(settings.jwt_secret)
    assert VALID_SECRET not in repr(settings.jwt_secret)


def test_jwt_secret_accepts_valid_random_secret() -> None:
    settings = Settings()

    assert settings.jwt_secret.get_secret_value() == VALID_SECRET


@pytest.mark.parametrize("value", ["", "   "])
def test_jwt_issuer_rejects_empty_or_whitespace(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("JWT_ISSUER", value)

    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("value", ["", "   "])
def test_jwt_audience_rejects_empty_or_whitespace(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("JWT_AUDIENCE", value)

    with pytest.raises(ValidationError):
        Settings()


def test_jwt_issuer_is_whitespace_trimmed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_ISSUER", "  business-management-platform  ")

    settings = Settings()

    assert settings.jwt_issuer == "business-management-platform"


def test_jwt_audience_is_whitespace_trimmed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_AUDIENCE", "  business-management-platform-api  ")

    settings = Settings()

    assert settings.jwt_audience == "business-management-platform-api"


def test_wildcard_cors_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["*"]')

    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("origin", ["http://*", "https://*.example.com"])
def test_cors_rejects_scheme_qualified_wildcard_host(
    monkeypatch: pytest.MonkeyPatch, origin: str
) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", f'["{origin}"]')

    with pytest.raises(ValidationError):
        Settings()


def test_cors_rejects_trailing_backslash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["http://example.com\\\\"]')

    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize(
    "invalid_origin",
    [
        "http://user:pass@localhost:5173",
        "http://localhost:5173/path",
        "http://localhost:5173?query=1",
        "http://localhost:5173#fragment",
    ],
)
def test_cors_origin_with_userinfo_path_query_or_fragment_rejected(
    monkeypatch: pytest.MonkeyPatch, invalid_origin: str
) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", f'["{invalid_origin}"]')

    with pytest.raises(ValidationError):
        Settings()


def test_cors_empty_list_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "[]")

    with pytest.raises(ValidationError):
        Settings()


def test_cors_accepts_explicit_localhost_http_origin() -> None:
    settings = Settings()

    assert settings.cors_allowed_origins == ["http://localhost:5173"]


def test_cors_rejects_duplicate_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["http://localhost:5173", "http://localhost:5173"]')

    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize(
    "origin", ["ftp://localhost:5173", "ws://localhost:5173", "file:///etc/passwd"]
)
def test_cors_rejects_non_http_https_scheme(monkeypatch: pytest.MonkeyPatch, origin: str) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", f'["{origin}"]')

    with pytest.raises(ValidationError):
        Settings()


def test_cors_malformed_non_json_input_raises_settings_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "not-json")

    with pytest.raises(SettingsError):
        Settings()


def test_cors_valid_json_but_non_array_shape_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '{"origin": "http://localhost:5173"}')

    with pytest.raises(ValidationError):
        Settings()


def test_cors_accepts_multiple_unique_explicit_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS", '["http://localhost:5173", "https://app.example.com"]'
    )

    settings = Settings()

    assert settings.cors_allowed_origins == [
        "http://localhost:5173",
        "https://app.example.com",
    ]


def test_cors_rejects_bare_trailing_slash_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["http://localhost:5173/"]')

    with pytest.raises(ValidationError):
        Settings()


def test_cors_accepts_uppercase_scheme_and_host_normalized_to_lowercase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["HTTP://LOCALHOST:5173"]')

    settings = Settings()

    assert settings.cors_allowed_origins == ["http://localhost:5173"]


def test_cors_rejects_case_equivalent_duplicate_after_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["http://X:5173", "http://x:5173"]')

    with pytest.raises(ValidationError):
        Settings()


def test_cors_strips_default_http_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["HTTP://EXAMPLE.COM:80"]')

    settings = Settings()

    assert settings.cors_allowed_origins == ["http://example.com"]


def test_cors_strips_default_https_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["https://EXAMPLE.COM:443"]')

    settings = Settings()

    assert settings.cors_allowed_origins == ["https://example.com"]


def test_cors_rejects_implicit_and_explicit_default_port_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["http://example.com", "http://example.com:80"]')

    with pytest.raises(ValidationError):
        Settings()


def test_cors_preserves_non_default_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["https://example.com:8443"]')

    settings = Settings()

    assert settings.cors_allowed_origins == ["https://example.com:8443"]


@pytest.mark.parametrize("origin", ["http://", "http://:5173", "http://localhost:99999"])
def test_cors_rejects_hostless_or_malformed_origin(
    monkeypatch: pytest.MonkeyPatch, origin: str
) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", f'["{origin}"]')

    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize(
    "origin",
    [
        "http://@example.com",
        "http://example.com?",
        "http://example.com#",
        "http://example.com:",
    ],
)
def test_cors_rejects_empty_userinfo_query_fragment_or_port(
    monkeypatch: pytest.MonkeyPatch, origin: str
) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", f'["{origin}"]')

    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("invalid_value", ["prod", "Production", "dev", "staging", ""])
def test_environment_rejects_invalid_value(
    monkeypatch: pytest.MonkeyPatch, invalid_value: str
) -> None:
    monkeypatch.setenv("ENVIRONMENT", invalid_value)

    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_environment_accepts_approved_values(
    monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)

    settings = Settings()

    assert settings.environment == environment


def test_environment_has_no_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    with pytest.raises(ValidationError):
        Settings()


def test_log_level_defaults_to_info(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings()

    assert settings.log_level == "INFO"


@pytest.mark.parametrize(
    "level", ["debug", "Debug", "DEBUG", "info", "warning", "error", "critical"]
)
def test_log_level_accepted_case_insensitively_and_normalized(
    monkeypatch: pytest.MonkeyPatch, level: str
) -> None:
    monkeypatch.setenv("LOG_LEVEL", level)

    settings = Settings()

    assert settings.log_level == level.upper()


def test_log_level_rejects_invalid_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "TRACE")

    with pytest.raises(ValidationError):
        Settings()


def test_access_token_expire_minutes_defaults_to_15(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)

    settings = Settings()

    assert settings.access_token_expire_minutes == 15


def test_refresh_token_expire_days_defaults_to_14(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REFRESH_TOKEN_EXPIRE_DAYS", raising=False)

    settings = Settings()

    assert settings.refresh_token_expire_days == 14


@pytest.mark.parametrize("value", ["0", "-1"])
def test_access_token_expire_minutes_rejects_non_positive(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", value)

    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("value", ["0", "-1"])
def test_refresh_token_expire_days_rejects_non_positive(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", value)

    with pytest.raises(ValidationError):
        Settings()


def test_access_token_expire_minutes_accepts_very_large_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1000000000")

    settings = Settings()

    assert settings.access_token_expire_minutes == 1000000000


def test_refresh_token_expire_days_accepts_very_large_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "1000000000")

    settings = Settings()

    assert settings.refresh_token_expire_days == 1000000000


@pytest.mark.parametrize(
    "scheme_url",
    [
        "mysql://postgres:postgres@localhost:3306/business_management_platform",
        "postgresql://postgres:postgres@localhost:5432/business_management_platform",
        "not-a-url",
    ],
)
def test_database_url_rejects_non_postgresql_psycopg_scheme(
    monkeypatch: pytest.MonkeyPatch, scheme_url: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", scheme_url)

    with pytest.raises(ValidationError):
        Settings()


def test_database_url_accepts_postgresql_psycopg_scheme() -> None:
    settings = Settings()

    assert settings.database_url.startswith("postgresql+psycopg://")


def test_production_configuration_rejects_placeholder_jwt_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", ENV_EXAMPLE_SENTINEL)

    with pytest.raises(ValidationError):
        Settings()


def test_production_configuration_rejects_wildcard_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["*"]')

    with pytest.raises(ValidationError):
        Settings()


def test_production_configuration_accepts_fully_valid_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")

    settings = Settings()

    assert settings.environment == "production"
