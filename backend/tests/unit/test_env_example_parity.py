from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import JWT_SECRET_SENTINEL, Settings

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"


def _parsed_env_example_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in ENV_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name, _, value = stripped.partition("=")
        values[name.strip()] = value
    return values


def _parsed_env_example_keys() -> set[str]:
    return set(_parsed_env_example_values())


def test_env_example_exposed_keys_match_settings_model() -> None:
    settings_keys = {name.upper() for name in Settings.model_fields}

    assert _parsed_env_example_keys() == settings_keys


def test_env_example_jwt_secret_matches_sentinel_constant() -> None:
    assert _parsed_env_example_values()["JWT_SECRET"] == JWT_SECRET_SENTINEL


def test_env_example_is_rejected_as_valid_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _parsed_env_example_keys():
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=str(ENV_EXAMPLE_PATH))
