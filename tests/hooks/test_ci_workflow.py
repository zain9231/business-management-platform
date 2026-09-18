"""Contract tests for the P1-07 continuous-integration implementation."""

from __future__ import annotations

import importlib.util
import re
import shlex
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, cast

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
VALIDATOR = REPOSITORY_ROOT / "scripts" / "validate_migrations.py"
PYPROJECT = REPOSITORY_ROOT / "backend" / "pyproject.toml"
RUNTIME_LOCK = REPOSITORY_ROOT / "backend" / "requirements.txt"
DEV_LOCK = REPOSITORY_ROOT / "backend" / "requirements-dev.txt"
DOCKERFILE = REPOSITORY_ROOT / "backend" / "Dockerfile"

ACTION_PINS = {
    "actions/checkout": ("3d3c42e5aac5ba805825da76410c181273ba90b1", "v7.0.1"),
    "actions/setup-python": ("5fda3b95a4ea91299a34e894583c3862153e4b97", "v7.0.0"),
    "actions/cache": ("55cc8345863c7cc4c66a329aec7e433d2d1c52a9", "v6.1.0"),
}
POSTGRES_IMAGE = (
    "postgres:18.6-bookworm@sha256:b939b3851e2cccb017dc4497af63b15e34efa57fba036548773c53b2f16a8871"
)
GITLEAKS_ARCHIVE_SHA256 = "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"


class MigrationValidator(Protocol):
    TRANSITION_MESSAGE: str

    def validate_repository(
        self,
        repository_root: Path,
        *,
        tracked_python_files: Sequence[Path] | None = None,
    ) -> list[str]: ...


def _required_text(path: Path) -> str:
    assert path.is_file(), f"required P1-07 file is missing: {path.relative_to(REPOSITORY_ROOT)}"
    return path.read_text(encoding="utf-8")


def _load_validator() -> MigrationValidator:
    assert VALIDATOR.is_file(), "scripts/validate_migrations.py is missing"
    spec = importlib.util.spec_from_file_location("validate_migrations", VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(MigrationValidator, module)


def _generated_command(lock_text: str) -> list[str]:
    prefix = "#    "
    command_line = next(
        line.removeprefix(prefix) for line in lock_text.splitlines() if line.startswith(prefix)
    )
    return shlex.split(command_line)


def test_p1_07_owned_files_exist() -> None:
    assert WORKFLOW.is_file()
    assert VALIDATOR.is_file()
    assert DEV_LOCK.is_file()


def test_workflow_has_safe_triggers_permissions_and_concurrency() -> None:
    text = _required_text(WORKFLOW)

    assert re.search(r"(?m)^name: CI$", text)
    assert re.search(r"(?m)^  pull_request:$", text)
    assert re.search(r"(?m)^  push:$", text)
    assert re.search(r"(?m)^  workflow_dispatch:$", text)
    assert "pull_request_target" not in text
    assert "paths:" not in text
    assert "secrets." not in text
    assert re.search(r"(?ms)^permissions:\n  contents: read$", text)
    assert (
        "group: ci-${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}"
        in text
    )
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in text
    assert "runs-on: ubuntu-24.04" in text
    assert "timeout-minutes: 30" in text


def test_workflow_pins_actions_service_and_checkout_boundary() -> None:
    text = _required_text(WORKFLOW)

    for action, (commit, version) in ACTION_PINS.items():
        assert f"uses: {action}@{commit}  # {version}" in text
    assert POSTGRES_IMAGE in text
    assert "persist-credentials: false" in text
    assert "fetch-depth: 1" in text
    assert "POSTGRES_DB: postgres" in text
    assert '--health-cmd "pg_isready -U postgres -d postgres"' in text


def test_workflow_pins_dependency_and_cache_contract() -> None:
    text = _required_text(WORKFLOW)

    assert "python-version: '3.13.15'" in text
    assert "python -m pip --version" in text
    assert (
        "python -m pip install --require-hashes --requirement backend/requirements-dev.txt" in text
    )
    assert 'test "$pip_version" = "26.2.1"' in text
    assert "python -m pip check" in text
    assert "path: ${{ steps.pip-cache.outputs.dir }}" in text
    assert "hashFiles('backend/requirements.txt', 'backend/requirements-dev.txt')" in text
    assert 'lock_repro_root="$RUNNER_TEMP/lock-repro"' in text
    assert 'git archive HEAD backend | tar -x -C "$lock_repro_root"' in text
    assert "pip-compile --allow-unsafe --generate-hashes" in text
    assert "pip-compile --allow-unsafe --extra dev --generate-hashes" in text
    assert "diff -u backend/requirements.txt" in text
    assert "diff -u backend/requirements-dev.txt" in text
    assert ".venv" not in text


def test_workflow_has_postgresql_and_secret_failure_boundaries() -> None:
    text = _required_text(WORKFLOW)

    assert "postgresql://postgres:postgres@127.0.0.1:5432/postgres" in text
    assert "connect_timeout=5" in text
    assert "readiness_result=\"$(python - <<'PY'" in text
    assert 'leftover_databases="$(docker exec "${{ job.services.postgres.id }}"' in text
    assert "^bmp_test_[0-9a-f]{32}$" in text
    assert "Leftover run-owned databases:" in text
    assert 'if [[ -n "$leftover_databases" ]]' in text
    assert GITLEAKS_ARCHIVE_SHA256 in text
    assert "gitleaks_8.30.1_linux_x64.tar.gz" in text
    assert "--exit-code 42" in text
    assert "aws-access-token" in text
    assert text.count("gitleaks dir --redact --no-banner --verbose .") == 2
    assert "SKIP=gitleaks,gitleaks-dir python -m pre_commit run --all-files" in text


def test_workflow_runs_the_required_gates_in_order() -> None:
    text = _required_text(WORKFLOW)
    markers = [
        "python scripts/quality.py lint",
        "python scripts/quality.py typecheck",
        "python scripts/validate_migrations.py",
        "backend/tests -m unit",
        "backend/tests -p no:cacheprovider",
        "python -m pytest tests/hooks",
        "SKIP=gitleaks,gitleaks-dir python -m pre_commit run --all-files",
        'checkout_status="$(git status --porcelain=v1 --untracked-files=all --ignored)"',
        "sha256sum -c docs/project/phase-0-artifacts.sha256",
    ]
    positions = [text.index(marker) for marker in markers]

    assert positions == sorted(positions)
    assert "TEST_DATABASE_URL=not-a-database-url" in text
    assert (
        "TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/bmp_test" in text
    )
    assert '--basetemp="$RUNNER_TEMP/pytest-unit"' in text
    assert '--basetemp="$RUNNER_TEMP/pytest-full"' in text
    assert '--basetemp="$RUNNER_TEMP/pytest-tooling"' in text
    assert "git diff --exit-code" in text
    assert 'test -z "$checkout_status"' in text


def test_dependency_sources_and_hash_locks_are_explicit() -> None:
    config = tomllib.loads(_required_text(PYPROJECT))
    dev_dependencies = config["project"]["optional-dependencies"]["dev"]
    runtime_lock = _required_text(RUNTIME_LOCK)
    dev_lock = _required_text(DEV_LOCK)
    dockerfile = _required_text(DOCKERFILE)
    runtime_command = _generated_command(runtime_lock)
    dev_command = _generated_command(dev_lock)

    assert dev_dependencies.count("pip==26.2.1") == 1
    assert runtime_command[0] == "pip-compile"
    assert "--allow-unsafe" in runtime_command
    assert "--generate-hashes" in runtime_command
    assert "--output-file=requirements.txt" in runtime_command
    assert runtime_command[-1] == "pyproject.toml"
    assert dev_command[0] == "pip-compile"
    assert "--allow-unsafe" in dev_command
    assert "--extra=dev" in dev_command
    assert "--generate-hashes" in dev_command
    assert "--output-file=requirements-dev.txt" in dev_command
    assert dev_command[-1] == "pyproject.toml"
    assert "pip==26.2.1" in dev_lock
    assert "--hash=sha256:" in runtime_lock
    assert "--hash=sha256:" in dev_lock
    assert "python -m pip install --require-hashes --requirement requirements.txt" in dockerfile


def test_migration_validator_accepts_the_current_absent_state(tmp_path: Path) -> None:
    validator = _load_validator()

    assert validator.validate_repository(tmp_path, tracked_python_files=[]) == []
    assert "P2-01" in validator.TRANSITION_MESSAGE
    assert "upgrade" in validator.TRANSITION_MESSAGE
    assert "downgrade" in validator.TRANSITION_MESSAGE
    assert "replay" in validator.TRANSITION_MESSAGE


@pytest.mark.parametrize("relative_path", ["backend/alembic.ini", "backend/alembic"])
def test_migration_validator_rejects_each_partial_surface(
    tmp_path: Path,
    relative_path: str,
) -> None:
    validator = _load_validator()
    candidate = tmp_path / relative_path
    if candidate.suffix:
        candidate.parent.mkdir(parents=True)
        candidate.write_text("[alembic]\n", encoding="utf-8")
    else:
        candidate.mkdir(parents=True)

    errors = validator.validate_repository(tmp_path, tracked_python_files=[])

    assert errors
    assert relative_path in "\n".join(errors)


@pytest.mark.parametrize(
    "source",
    [
        "import alembic\n",
        "from alembic import command\n",
        'revision = "001"\n',
    ],
)
def test_migration_validator_rejects_tracked_python_markers(
    tmp_path: Path,
    source: str,
) -> None:
    validator = _load_validator()
    tracked = tmp_path / "backend" / "probe.py"
    tracked.parent.mkdir(parents=True)
    tracked.write_text(source, encoding="utf-8")

    errors = validator.validate_repository(tmp_path, tracked_python_files=[tracked])

    assert errors
    assert "backend/probe.py" in "\n".join(errors)
