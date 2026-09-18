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
EXPECTED_TRIGGER_BLOCK = """\
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
  workflow_dispatch:
"""
JOB_ENV_ALLOWED_CONTEXTS = frozenset(
    {"github", "inputs", "matrix", "needs", "secrets", "strategy", "vars"}
)


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


def _assert_exact_trigger_block(text: str) -> None:
    assert text.count(EXPECTED_TRIGGER_BLOCK) == 1
    assert len(re.findall(r"(?m)^on:$", text)) == 1


def test_p1_07_owned_files_exist() -> None:
    assert WORKFLOW.is_file()
    assert VALIDATOR.is_file()
    assert DEV_LOCK.is_file()


def test_workflow_has_safe_triggers_permissions_and_concurrency() -> None:
    text = _required_text(WORKFLOW)

    assert re.search(r"(?m)^name: CI$", text)
    _assert_exact_trigger_block(text)
    assert "pull_request_target" not in text
    assert "paths:" not in text
    assert "secrets." not in text
    assert text.count("permissions:\n  contents: read\n") == 1
    assert (
        text.count(
            "concurrency:\n"
            "  group: ci-${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}\n"
            "  cancel-in-progress: ${{ github.event_name == 'pull_request' }}\n"
        )
        == 1
    )
    assert text.count("    runs-on: ubuntu-24.04\n") == 1
    assert text.count("    timeout-minutes: 30\n") == 1


def test_workflow_job_env_uses_only_available_contexts() -> None:
    text = _required_text(WORKFLOW)
    match = re.search(r"(?m)^    env:\n(?P<body>(?:      [^\n]*\n)+)", text)

    assert match is not None, "CI job env block is missing"
    context_roots = set(re.findall(r"\$\{\{\s*([A-Za-z_][A-Za-z0-9_-]*)", match.group("body")))
    unavailable_contexts = context_roots - JOB_ENV_ALLOWED_CONTEXTS
    assert not unavailable_contexts, (
        f"CI job env uses contexts unavailable at jobs.<job_id>.env: {sorted(unavailable_contexts)}"
    )


def test_workflow_scopes_pre_commit_home_to_pre_commit_step() -> None:
    text = _required_text(WORKFLOW)
    match = re.search(
        r"(?ms)^      - name: Run non-Gitleaks pre-commit hooks\n"
        r"(?P<body>.*?)(?=^      - name:|\Z)",
        text,
    )

    assert match is not None, "non-Gitleaks pre-commit step is missing"
    assert (
        "        env:\n          PRE_COMMIT_HOME: ${{ runner.temp }}/pre-commit\n"
    ) in match.group(0)
    assert text.count("PRE_COMMIT_HOME:") == 1


def test_workflow_pins_actions_service_and_checkout_boundary() -> None:
    text = _required_text(WORKFLOW)

    expected_uses = [
        f"        uses: {action}@{commit}  # {version}"
        for action, (commit, version) in ACTION_PINS.items()
    ]
    assert re.findall(r"(?m)^        uses: .+$", text) == expected_uses
    assert text.count(f"        image: {POSTGRES_IMAGE}\n") == 1
    assert text.count("          persist-credentials: false\n") == 1
    assert text.count("          fetch-depth: 1\n") == 1
    assert text.count("          POSTGRES_DB: postgres\n") == 1
    assert text.count('          --health-cmd "pg_isready -U postgres -d postgres"\n') == 1


def test_workflow_pins_dependency_and_cache_contract() -> None:
    text = _required_text(WORKFLOW)

    assert text.count("          python-version: '3.13.15'\n") == 1
    assert text.count("          python -m pip --version\n") == 1
    assert (
        text.count(
            "          python -m pip install --require-hashes --requirement "
            "backend/requirements-dev.txt\n"
        )
        == 1
    )
    assert text.count('          test "$pip_version" = "26.2.1"\n') == 1
    assert text.count("          python -m pip check\n") == 3
    assert text.count("          path: ${{ steps.pip-cache.outputs.dir }}\n") == 1
    assert text.count("hashFiles('backend/requirements.txt', 'backend/requirements-dev.txt')") == 1
    assert text.count('          lock_repro_root="$RUNNER_TEMP/lock-repro"\n') == 1
    assert text.count('          git archive HEAD backend | tar -x -C "$lock_repro_root"\n') == 1
    assert (
        text.count(
            "            pip-compile --allow-unsafe --generate-hashes \\\n"
            "              --output-file=requirements.txt pyproject.toml\n"
        )
        == 1
    )
    assert (
        text.count(
            "            pip-compile --allow-unsafe --extra dev --generate-hashes \\\n"
            "              --output-file=requirements-dev.txt pyproject.toml\n"
        )
        == 1
    )
    assert (
        text.count(
            '          if ! diff -u backend/requirements.txt "$lock_repro_root/backend/requirements.txt"; '
            "then\n"
        )
        == 1
    )
    assert (
        text.count(
            "          if ! diff -u backend/requirements-dev.txt "
            '"$lock_repro_root/backend/requirements-dev.txt"; then\n'
        )
        == 1
    )
    assert ".venv" not in text


def test_workflow_has_postgresql_and_secret_failure_boundaries() -> None:
    text = _required_text(WORKFLOW)

    assert text.count("postgresql://postgres:postgres@127.0.0.1:5432/postgres") == 1
    assert text.count("              connect_timeout=5,\n") == 1
    assert text.count("          readiness_result=\"$(python - <<'PY'\n") == 1
    assert (
        text.count(
            '          leftover_databases="$(docker exec "${{ job.services.postgres.id }}" \\\n'
        )
        == 1
    )
    assert text.count("^bmp_test_[0-9a-f]{32}$") == 1
    assert text.count('            echo "Leftover run-owned databases:"\n') == 1
    assert text.count('          if [[ -n "$leftover_databases" ]]; then\n') == 1
    assert text.count(GITLEAKS_ARCHIVE_SHA256) == 1
    assert text.count("gitleaks_8.30.1_linux_x64.tar.gz") == 2
    assert text.count("--exit-code 42") == 1
    assert text.count("aws-access-token") == 1
    assert text.count("gitleaks dir --redact --no-banner --verbose .") == 2
    assert (
        text.count(
            "          SKIP=gitleaks,gitleaks-dir python -m pre_commit run --all-files "
            "--show-diff-on-failure\n"
        )
        == 1
    )


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
    assert all(text.count(marker) == 1 for marker in markers)
    positions = [text.index(marker) for marker in markers]

    assert positions == sorted(positions)
    assert text.count("TEST_DATABASE_URL=not-a-database-url") == 1
    assert (
        text.count(
            "TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/bmp_test"
        )
        == 1
    )
    assert text.count('--basetemp="$RUNNER_TEMP/pytest-unit"') == 1
    assert text.count('--basetemp="$RUNNER_TEMP/pytest-full"') == 1
    assert text.count('--basetemp="$RUNNER_TEMP/pytest-tooling"') == 1
    assert text.count("git diff --exit-code") == 1
    assert text.count('test -z "$checkout_status"') == 1


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
