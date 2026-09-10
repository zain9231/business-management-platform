import json
from typing import TypedDict
from urllib.parse import urlsplit

from pydantic import AnyUrl, SecretStr, TypeAdapter, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, SettingsError
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

PLACEHOLDER_MARKERS = (
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
)

JWT_SECRET_SENTINEL = "replace-me-with-at-least-32-random-bytes"

ALLOWED_ENVIRONMENTS = frozenset({"development", "test", "production"})
ALLOWED_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
DEFAULT_PORTS = {"http": 80, "https": 443}

_origin_adapter: TypeAdapter[AnyUrl] = TypeAdapter(AnyUrl)


class ConfigurationIssue(TypedDict):
    loc: tuple[str | int, ...]
    msg: str


class ConfigurationError(ValueError):
    """Configuration diagnostics containing only field locations and safe reasons."""

    def __init__(self, issues: list[ConfigurationIssue]) -> None:
        self._issues = tuple((issue["loc"], issue["msg"]) for issue in issues)
        details = "; ".join(
            f"{'.'.join(map(str, loc)) or 'settings'}: {msg}" for loc, msg in self._issues
        )
        super().__init__(f"Invalid configuration: {details}")

    def errors(self) -> list[ConfigurationIssue]:
        return [{"loc": loc, "msg": msg} for loc, msg in self._issues]

    def json(self) -> str:
        return json.dumps(self.errors())


class Settings(BaseSettings):
    # SecretStr alone does not redact the raw input attached to validation errors.
    model_config = SettingsConfigDict(hide_input_in_errors=True)

    database_url: str
    jwt_secret: SecretStr
    jwt_issuer: str
    jwt_audience: str
    cors_allowed_origins: list[str]
    environment: str
    log_level: str = "INFO"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        try:
            url = make_url(value)
        except (ArgumentError, ValueError) as exc:
            raise ValueError("DATABASE_URL must be a valid SQLAlchemy URL") from exc
        if url.drivername != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use the postgresql+psycopg driver")
        return value

    @field_validator("jwt_secret")
    @classmethod
    def _validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        stripped = value.get_secret_value().strip()
        lowered = stripped.lower()
        if lowered == JWT_SECRET_SENTINEL or any(
            marker in lowered for marker in PLACEHOLDER_MARKERS
        ):
            raise ValueError("JWT_SECRET must not contain a placeholder marker")
        if len(stripped.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET must be at least 32 UTF-8 bytes")
        return SecretStr(stripped)

    @field_validator("jwt_issuer", "jwt_audience")
    @classmethod
    def _validate_non_empty_trimmed(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("cors_allowed_origins")
    @classmethod
    def _validate_cors_allowed_origins(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("CORS_ALLOWED_ORIGINS must contain at least one origin")

        canonical_origins = [cls._canonicalize_origin(origin) for origin in value]

        if len(set(canonical_origins)) != len(canonical_origins):
            raise ValueError("CORS_ALLOWED_ORIGINS must not contain duplicate origins")

        return canonical_origins

    @staticmethod
    def _canonicalize_origin(origin: str) -> str:
        if origin == "*":
            raise ValueError("CORS_ALLOWED_ORIGINS must not contain a wildcard origin")
        if "\\" in origin:
            raise ValueError("CORS_ALLOWED_ORIGINS origins must not contain a backslash")

        try:
            parts = urlsplit(origin)
        except ValueError as exc:
            raise ValueError("CORS_ALLOWED_ORIGINS origins must be valid URLs") from exc

        if parts.path:
            raise ValueError("CORS_ALLOWED_ORIGINS origins must not contain a path")
        if parts.username is not None or parts.password is not None:
            raise ValueError("CORS_ALLOWED_ORIGINS origins must not contain userinfo")
        # urlsplit normalizes both "no query"/"no fragment" and "present but empty" to "",
        # so component presence is checked on the raw string rather than parts.query/fragment.
        if "?" in origin:
            raise ValueError("CORS_ALLOWED_ORIGINS origins must not contain a query")
        if "#" in origin:
            raise ValueError("CORS_ALLOWED_ORIGINS origins must not contain a fragment")
        if parts.netloc.endswith(":"):
            raise ValueError("CORS_ALLOWED_ORIGINS origins must not contain an empty port")

        try:
            parsed = _origin_adapter.validate_python(origin)
        except ValidationError as exc:
            raise ValueError("CORS_ALLOWED_ORIGINS origins must be valid URLs") from exc

        if parsed.scheme not in ("http", "https"):
            raise ValueError("CORS_ALLOWED_ORIGINS origins must use http or https")
        if not parsed.host:
            raise ValueError("CORS_ALLOWED_ORIGINS origins must have a hostname")
        if "*" in parsed.host:
            raise ValueError("CORS_ALLOWED_ORIGINS origins must not contain a wildcard host")

        port = parsed.port
        if port == DEFAULT_PORTS.get(parsed.scheme):
            port = None

        canonical = f"{parsed.scheme}://{parsed.host}"
        if port is not None:
            canonical += f":{port}"
        return canonical

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        if value not in ALLOWED_ENVIRONMENTS:
            raise ValueError("ENVIRONMENT must be one of development, test, production")
        return value

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in ALLOWED_LOG_LEVELS:
            raise ValueError("LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL")
        return normalized

    @field_validator("access_token_expire_minutes", "refresh_token_expire_days")
    @classmethod
    def _validate_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be a positive integer")
        return value


def load_settings() -> Settings:
    """Construct application settings through the confidential diagnostic boundary.

    Direct construction retains inputs in structured Pydantic errors; see
    test_direct_settings_construction_is_not_confidential_by_design. Validators
    must keep their messages free of input values. Source parsing failures use
    a fixed message because SettingsError has no structured safe diagnostics.
    """
    try:
        return Settings()
    except ValidationError as exc:
        issues: list[ConfigurationIssue] = [
            {"loc": error["loc"], "msg": error["msg"]}
            for error in exc.errors(include_url=False, include_input=False, include_context=False)
        ]
    except SettingsError:
        issues = [{"loc": (), "msg": "Unable to parse configuration from environment variables"}]

    # Outside the handlers so the original exception is not retained as context.
    raise ConfigurationError(issues) from None
