"""Behavioral contract tests for the cross-platform quality runner."""

from __future__ import annotations

import importlib
import importlib.util
import io
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
PYPROJECT = BACKEND_ROOT / "pyproject.toml"
RUNNER = REPO_ROOT / "scripts" / "quality.py"
FORMAT_AFTER_EDIT = REPO_ROOT / ".claude" / "hooks" / "format_after_edit.py"
FRONTEND_ROOT = REPO_ROOT / "frontend"
PRETTIER_CONFIG = FRONTEND_ROOT / ".prettierrc.json"
PRETTIER_IGNORE = FRONTEND_ROOT / ".prettierignore"
ESLINT_CONFIG = FRONTEND_ROOT / "eslint.config.mjs"
PRE_COMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
CLAUDE_SETTINGS = REPO_ROOT / ".claude" / "settings.json"
PHASE_0_MANIFEST = REPO_ROOT / "docs" / "project" / "phase-0-artifacts.sha256"
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"
GENERATED_FRONTEND_PATHS = (
    "node_modules",
    "dist",
    "coverage",
    ".vite",
    "playwright-report",
    "test-results",
)
PRE_COMMIT_HOOKS_REPOSITORY = "https://github.com/pre-commit/pre-commit-hooks"
RUFF_PRE_COMMIT_REPOSITORY = "https://github.com/astral-sh/ruff-pre-commit"
GITLEAKS_REPOSITORY = "https://github.com/gitleaks/gitleaks"
RUFF_HOOK_FILES = r"^(backend/|tests/|scripts/).*\.py$"
DBML_EXCLUDE = r"^docs/architecture/erd/source/business-management-platform-erd-v1\.2\.dbml$"
UPSTREAM_GITLEAKS_ENTRY = "gitleaks git --pre-commit --redact --staged --verbose"
MUTATING_TEXT_HOOK_IDS = (
    "trailing-whitespace",
    "end-of-file-fixer",
    "mixed-line-ending",
    "fix-byte-order-marker",
)
OWNED_TARGETS = ["app", "tests", "../tests", "../scripts/quality.py"]
RUFF_PREFIX = [sys.executable, "-m", "ruff"]
EXPECTED_COMMANDS = {
    "format": [
        [*RUFF_PREFIX, "check", "--fix", "--no-cache", *OWNED_TARGETS],
        [*RUFF_PREFIX, "format", "--no-cache", *OWNED_TARGETS],
    ],
    "lint": [
        [*RUFF_PREFIX, "format", "--check", "--no-cache", *OWNED_TARGETS],
        [*RUFF_PREFIX, "check", "--no-cache", *OWNED_TARGETS],
    ],
    "typecheck": [[sys.executable, "-m", "mypy", "--cache-dir", os.devnull]],
}


class YamlModule(Protocol):
    def safe_load(self, stream: str) -> object: ...


class QualityModule(Protocol):
    PYTHON_TARGETS: tuple[str, ...]

    def main(self, argv: Sequence[str] | None = None) -> int: ...


@dataclass(frozen=True)
class RunCall:
    argv: list[str]
    cwd: Path
    env: dict[str, str]
    check: bool
    shell: bool


def _load_quality() -> QualityModule:
    if not RUNNER.is_file():
        raise AssertionError("scripts/quality.py does not exist")

    spec = importlib.util.spec_from_file_location("quality", RUNNER)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load scripts/quality.py")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(QualityModule, module)


def _load_pre_commit_config() -> tuple[str, dict[str, object]]:
    if not PRE_COMMIT_CONFIG.is_file():
        raise AssertionError(".pre-commit-config.yaml does not exist")

    text = PRE_COMMIT_CONFIG.read_text(encoding="utf-8")
    yaml_module = cast(YamlModule, importlib.import_module("yaml"))
    loaded = yaml_module.safe_load(text)
    assert isinstance(loaded, dict)
    return text, cast(dict[str, object], loaded)


def _pre_commit_repositories(config: Mapping[str, object]) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], config["repos"])


def _pre_commit_hooks(repository: Mapping[str, object]) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], repository["hooks"])


def _pre_commit_repository(config: Mapping[str, object], repository_url: str) -> dict[str, object]:
    matches = [
        repository
        for repository in _pre_commit_repositories(config)
        if repository["repo"] == repository_url
    ]
    assert len(matches) == 1
    return matches[0]


@pytest.fixture
def quality_module() -> QualityModule:
    return _load_quality()


def _record_subprocess_runs(
    monkeypatch: pytest.MonkeyPatch, statuses: tuple[int, ...]
) -> list[RunCall]:
    calls: list[RunCall] = []
    status_iterator = iter(statuses)

    def available_spec(_tool: str) -> object:
        return object()

    def fake_run(
        argv: list[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        check: bool,
        shell: bool,
    ) -> subprocess.CompletedProcess[bytes]:
        calls.append(RunCall(list(argv), cwd, dict(env), check, shell))
        return subprocess.CompletedProcess(
            argv,
            next(status_iterator),
            stdout=b"",
            stderr=b"",
        )

    monkeypatch.setattr(importlib.util, "find_spec", available_spec)
    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_mypy_is_strict_and_enables_pydantic_settings_support() -> None:
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dev_dependencies = config["project"]["optional-dependencies"]["dev"]

    assert dev_dependencies.count("mypy==2.3.1") == 1
    assert config["tool"]["mypy"] == {
        "python_version": "3.13",
        "plugins": ["pydantic.mypy"],
        "strict": True,
        "incremental": False,
        "warn_unreachable": True,
        "warn_unused_configs": True,
        "show_error_codes": True,
        "files": OWNED_TARGETS,
    }
    assert config["tool"]["pydantic-mypy"] == {
        "init_forbid_extra": True,
        "init_typed": True,
        "warn_required_dynamic_aliases": True,
    }


def test_quality_runner_exposes_format_lint_and_typecheck(
    quality_module: QualityModule,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as raised:
        quality_module.main(["--help"])

    assert raised.value.code == 0
    assert "{format,lint,typecheck}" in capsys.readouterr().out


def test_owned_python_targets_include_repository_tooling_tests(
    quality_module: QualityModule,
) -> None:
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    assert list(quality_module.PYTHON_TARGETS) == OWNED_TARGETS
    assert config["tool"]["mypy"]["files"] == OWNED_TARGETS


def test_ruff_pin_and_first_party_policy_are_explicit() -> None:
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dev_dependencies = config["project"]["optional-dependencies"]["dev"]

    assert dev_dependencies.count("ruff==0.16.3") == 1
    assert config["tool"]["ruff"] == {
        "line-length": 100,
        "target-version": "py313",
        "required-version": "==0.16.3",
        "lint": {"isort": {"known-first-party": ["app"]}},
    }


def test_quality_runner_uses_argument_arrays_owned_targets_stable_cwd_and_hostile_env_guards(
    quality_module: QualityModule,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MYPY_CACHE_DIR", "hostile-cache")
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "0")
    monkeypatch.setenv("QUALITY_RUNNER_SENTINEL", "preserved")

    for command, expected_argv in EXPECTED_COMMANDS.items():
        calls = _record_subprocess_runs(monkeypatch, (0,) * len(expected_argv))

        assert quality_module.main([command]) == 0
        assert [call.argv for call in calls] == expected_argv
        assert all(isinstance(call.argv, list) for call in calls)
        assert all(call.cwd == BACKEND_ROOT for call in calls)
        assert all(call.check is False for call in calls)
        assert all(call.shell is False for call in calls)
        assert all(call.env["MYPY_CACHE_DIR"] == os.devnull for call in calls)
        assert all(call.env["PYTHONDONTWRITEBYTECODE"] == "1" for call in calls)
        assert all(call.env["QUALITY_RUNNER_SENTINEL"] == "preserved" for call in calls)

    assert os.environ["MYPY_CACHE_DIR"] == "hostile-cache"
    assert os.environ["PYTHONDONTWRITEBYTECODE"] == "0"


def test_quality_runner_propagates_failure_reports_missing_tool_and_frontend_deferral(
    quality_module: QualityModule,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    failure_cases = (
        ("format", (41, 0), 41, 1),
        ("lint", (0, 42), 42, 2),
    )
    for command, statuses, expected_status, expected_call_count in failure_cases:
        calls = _record_subprocess_runs(monkeypatch, statuses)

        assert quality_module.main([command]) == expected_status
        assert len(calls) == expected_call_count

    capsys.readouterr()

    def missing_spec(_tool: str) -> None:
        return None

    def unexpected_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        pytest.fail("a subprocess must not start when its required tool is unavailable")

    monkeypatch.setattr(importlib.util, "find_spec", missing_spec)
    monkeypatch.setattr(subprocess, "run", unexpected_run)

    for command, tool in (("format", "ruff"), ("lint", "ruff"), ("typecheck", "mypy")):
        assert quality_module.main([command]) == 127
        error = capsys.readouterr().err
        assert f"required tool '{tool}' is unavailable" in error
        assert "Install" in error
        assert 'python -m pip install -e "backend[dev]"' in error

    for command in ("format", "lint"):
        calls = _record_subprocess_runs(monkeypatch, (0, 0))

        assert quality_module.main([command]) == 0
        assert calls
        captured = capsys.readouterr()
        message = captured.out + captured.err
        assert message.count("P6-01") == 1
        assert "deferred" in message.lower()
        assert "no frontend command was run" in message.lower()
        assert "success" not in message.lower()


def test_frontend_placeholders_are_configuration_only_until_p6_01() -> None:
    placeholder_paths = (PRETTIER_CONFIG, PRETTIER_IGNORE, ESLINT_CONFIG)
    missing = [
        path.relative_to(REPO_ROOT).as_posix() for path in placeholder_paths if not path.is_file()
    ]
    assert not missing, f"frontend placeholder files are missing: {missing}"

    prettier_config = cast(
        dict[str, object],
        json.loads(PRETTIER_CONFIG.read_text(encoding="utf-8")),
    )
    assert prettier_config == {
        "endOfLine": "lf",
        "printWidth": 100,
        "singleQuote": True,
        "trailingComma": "all",
    }

    prettier_ignore = PRETTIER_IGNORE.read_text(encoding="utf-8")
    assert "P6-01" in prettier_ignore
    ignore_entries = {
        line for line in prettier_ignore.splitlines() if line and not line.startswith("#")
    }
    assert ignore_entries == {f"{path}/" for path in GENERATED_FRONTEND_PATHS}

    eslint_config = ESLINT_CONFIG.read_text(encoding="utf-8")
    assert "P6-01" in eslint_config
    assert "export default" in eslint_config
    assert "ignores:" in eslint_config
    for path in GENERATED_FRONTEND_PATHS:
        assert f"'{path}/**'" in eslint_config
    for active_fragment in (
        "import ",
        "files:",
        "languageOptions:",
        "plugins:",
        "rules:",
    ):
        assert active_fragment not in eslint_config

    frontend_entries = {path.name for path in FRONTEND_ROOT.iterdir()}
    assert frontend_entries == {
        ".prettierignore",
        ".prettierrc.json",
        "README.md",
        "eslint.config.mjs",
    }


def test_pre_commit_revisions_are_immutable_and_documented() -> None:
    config_text, config = _load_pre_commit_config()
    expected_repositories = (
        (
            PRE_COMMIT_HOOKS_REPOSITORY,
            "3e8a8703264a2f4a69428a0aa4dcb512790b2c8c",
            "v6.0.0",
            (
                "trailing-whitespace",
                "end-of-file-fixer",
                "mixed-line-ending",
                "fix-byte-order-marker",
                "check-added-large-files",
                "check-merge-conflict",
                "check-json",
                "check-toml",
                "check-yaml",
            ),
        ),
        (
            RUFF_PRE_COMMIT_REPOSITORY,
            "65dbdb59d2f2d9c3bdc343c566821ad3319ddaa3",
            "v0.16.3",
            ("ruff-check", "ruff-format"),
        ),
        (
            GITLEAKS_REPOSITORY,
            "83d9cd684c87d95d656c1458ef04895a7f1cbd8e",
            "v8.30.1",
            ("gitleaks", "gitleaks"),
        ),
    )

    assert config["minimum_pre_commit_version"] == "4.6.2"
    repositories = _pre_commit_repositories(config)
    assert [repository["repo"] for repository in repositories] == [
        expected[0] for expected in expected_repositories
    ]

    for repository, expected in zip(repositories, expected_repositories, strict=True):
        _, revision, tag, hook_ids = expected
        assert repository["rev"] == revision
        assert re.fullmatch(r"[0-9a-f]{40}", revision)
        assert f"    rev: {revision}  # {tag}" in config_text.splitlines()
        assert [hook["id"] for hook in _pre_commit_hooks(repository)] == list(hook_ids)

    ruff_hooks = _pre_commit_hooks(_pre_commit_repository(config, RUFF_PRE_COMMIT_REPOSITORY))
    assert ruff_hooks == [
        {
            "id": "ruff-check",
            "args": ["--fix", "--no-cache", "--config=backend/pyproject.toml"],
            "files": RUFF_HOOK_FILES,
        },
        {
            "id": "ruff-format",
            "args": ["--no-cache", "--config=backend/pyproject.toml"],
            "files": RUFF_HOOK_FILES,
        },
    ]


def test_mutating_hooks_cannot_select_manifest_backed_text_artifacts() -> None:
    config_text, config = _load_pre_commit_config()
    contributing_patterns = [
        line[1:-1]
        for line in CONTRIBUTING.read_text(encoding="utf-8").splitlines()
        if line.startswith("`^docs/(") and line.endswith("`")
    ]
    assert len(contributing_patterns) == 1
    protected_text_exclude = f"{contributing_patterns[0]}|{DBML_EXCLUDE}"

    pre_commit_hooks = _pre_commit_hooks(
        _pre_commit_repository(config, PRE_COMMIT_HOOKS_REPOSITORY)
    )
    mutating_hooks = [hook for hook in pre_commit_hooks if hook["id"] in MUTATING_TEXT_HOOK_IDS]
    assert mutating_hooks == [
        {
            "id": "trailing-whitespace",
            "args": ["--markdown-linebreak-ext=md"],
            "exclude": protected_text_exclude,
        },
        {"id": "end-of-file-fixer", "exclude": protected_text_exclude},
        {
            "id": "mixed-line-ending",
            "args": ["--fix=lf"],
            "exclude": protected_text_exclude,
        },
        {"id": "fix-byte-order-marker", "exclude": protected_text_exclude},
    ]

    assert "exclude" not in config
    hooks_with_exclusions = [
        hook["id"]
        for repository in _pre_commit_repositories(config)
        for hook in _pre_commit_hooks(repository)
        if "exclude" in hook
    ]
    assert hooks_with_exclusions == list(MUTATING_TEXT_HOOK_IDS)
    expected_source_line = f"        exclude: '{protected_text_exclude}'"
    assert config_text.splitlines().count(expected_source_line) == 4

    manifest_paths = [
        line.split(maxsplit=1)[1]
        for line in PHASE_0_MANIFEST.read_text(encoding="utf-8").splitlines()
        if line
    ]
    protected_text_paths = [
        path for path in manifest_paths if Path(path).suffix in {".dbml", ".md"}
    ]
    assert len(protected_text_paths) == 8
    for hook in mutating_hooks:
        exclude = re.compile(cast(str, hook["exclude"]))
        selected_paths = [path for path in protected_text_paths if exclude.search(path) is None]
        assert not selected_paths, f"{hook['id']} can select: {selected_paths}"


def test_large_file_limit_is_2048_kib_and_secret_scanning_has_no_exclusion() -> None:
    _, config = _load_pre_commit_config()
    pre_commit_hooks = _pre_commit_hooks(
        _pre_commit_repository(config, PRE_COMMIT_HOOKS_REPOSITORY)
    )
    large_file_hooks = [
        hook for hook in pre_commit_hooks if hook["id"] == "check-added-large-files"
    ]
    assert large_file_hooks == [{"id": "check-added-large-files", "args": ["--maxkb=2048"]}]

    gitleaks_hooks = _pre_commit_hooks(_pre_commit_repository(config, GITLEAKS_REPOSITORY))
    assert len(gitleaks_hooks) == 2
    assert all("exclude" not in hook for hook in gitleaks_hooks)


def test_gitleaks_manual_current_tree_and_automatic_staged_hooks_are_distinct() -> None:
    config_text, config = _load_pre_commit_config()
    gitleaks_hooks = _pre_commit_hooks(_pre_commit_repository(config, GITLEAKS_REPOSITORY))
    assert gitleaks_hooks == [
        {"id": "gitleaks"},
        {
            "id": "gitleaks",
            "alias": "gitleaks-dir",
            "entry": "gitleaks dir --redact --verbose .",
            "pass_filenames": False,
            "always_run": True,
            "stages": ["manual"],
        },
    ]
    expected_upstream_comment = (
        f"      # Upstream staged entry: {UPSTREAM_GITLEAKS_ENTRY}; pass_filenames: false."
    )
    assert expected_upstream_comment in config_text.splitlines()
    assert "    # Neither hook scans Git history; P10-01 owns that coverage." in (
        config_text.splitlines()
    )


def test_claude_permissions_use_exact_nonshadowing_runner_rules() -> None:
    settings = cast(
        dict[str, object],
        json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8")),
    )
    permissions = cast(dict[str, object], settings["permissions"])
    buckets = {name: cast(list[str], permissions[name]) for name in ("allow", "ask", "deny")}
    expected = {
        "allow": [
            "Bash(python scripts/quality.py lint)",
            "Bash(python scripts/quality.py typecheck)",
        ],
        "ask": ["Bash(python scripts/quality.py format)"],
        "deny": [],
    }
    commands = [rule for rules in expected.values() for rule in rules]
    runner_prefix = "Bash(python scripts/quality.py"

    problems: list[str] = []
    for bucket in ("allow", "ask", "deny"):
        actual = [rule for rule in buckets[bucket] if rule.startswith(runner_prefix)]
        if actual != expected[bucket]:
            problems.append(
                f"{bucket} quality-runner rules were {actual!r}, expected {expected[bucket]!r}"
            )

    shadowing_wildcards: list[str] = []
    for bucket, rules in buckets.items():
        for rule in rules:
            if "*" not in rule:
                continue
            literal_prefix = rule.split("*", maxsplit=1)[0]
            if literal_prefix.endswith(":"):
                literal_prefix = literal_prefix[:-1] + " "
            if any(command.startswith(literal_prefix) for command in commands):
                shadowing_wildcards.append(f"{bucket}:{rule}")
    if shadowing_wildcards:
        problems.append(
            f"shadowing quality-runner wildcard rules were {shadowing_wildcards!r}, expected []"
        )

    assert not problems, "\n".join(problems)


def test_format_after_edit_reports_ruff_format_and_check_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    owned_targets = [
        tmp_path / "backend" / "app" / "broken.py",
        tmp_path / "tests" / "hooks" / "broken.py",
        tmp_path / "scripts" / "broken.py",
    ]
    for target in owned_targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("value=1\n", encoding="utf-8")
    unowned_target = tmp_path / ".claude" / "hooks" / "unowned.py"
    unowned_target.parent.mkdir(parents=True)
    unowned_target.write_text("value=1\n", encoding="utf-8")

    calls: list[tuple[list[str], Path]] = []

    def fake_run(
        argv: list[str],
        *,
        capture_output: bool,
        text: bool,
        timeout: int,
        cwd: str,
    ) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert text is True
        assert timeout == 45
        calls.append((list(argv), Path(cwd)))
        command = "check" if "check" in argv else "format"
        return subprocess.CompletedProcess(
            argv,
            41 if command == "check" else 42,
            stdout=f"{command} stdout marker\n",
            stderr=f"{command} stderr marker\n",
        )

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda module: (
            importlib.util.spec_from_loader(module, loader=None) if module == "ruff" else None
        ),
    )
    monkeypatch.setattr(shutil, "which", lambda _command: None)
    assert importlib.util.find_spec("ruff") is not None
    assert shutil.which("ruff") is None
    monkeypatch.setattr(subprocess, "run", fake_run)

    def run_hook(target: Path) -> tuple[int | str | None, str, str]:
        payload = json.dumps({"tool_input": {"file_path": str(target)}, "cwd": str(tmp_path)})
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        with pytest.raises(SystemExit) as raised:
            runpy.run_path(str(FORMAT_AFTER_EDIT), run_name="__main__")
        captured = capsys.readouterr()
        return raised.value.code, captured.out, captured.err

    problems: list[str] = []
    for owned_target in owned_targets:
        calls.clear()
        owned_exit, owned_stdout, owned_stderr = run_hook(owned_target)
        expected_calls = [
            (
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "check",
                    "--fix",
                    "--no-cache",
                    "--config=backend/pyproject.toml",
                    str(owned_target),
                ],
                tmp_path,
            ),
            (
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "format",
                    "--no-cache",
                    "--config=backend/pyproject.toml",
                    str(owned_target),
                ],
                tmp_path,
            ),
        ]
        relative_target = owned_target.relative_to(tmp_path).as_posix()
        if owned_exit != 0:
            problems.append(
                f"owned hook exit for {relative_target} was {owned_exit}, expected fail-open 0"
            )
        if owned_stdout:
            problems.append(
                f"owned hook wrote unexpected stdout for {relative_target}: {owned_stdout!r}"
            )
        if calls != expected_calls:
            problems.append(
                f"Ruff calls for {relative_target} were {calls!r}, expected {expected_calls!r}"
            )
        for fragment in (
            "ruff check --fix",
            relative_target,
            "check stdout marker",
            "check stderr marker",
            "ruff format",
            "format stdout marker",
            "format stderr marker",
        ):
            if fragment not in owned_stderr:
                problems.append(
                    f"owned stderr for {relative_target} is missing {fragment!r}: {owned_stderr!r}"
                )

    calls.clear()
    unowned_exit, unowned_stdout, unowned_stderr = run_hook(unowned_target)
    if unowned_exit != 0:
        problems.append(f"unowned hook exit was {unowned_exit}, expected 0")
    if unowned_stdout or unowned_stderr:
        problems.append(
            "unowned .claude/hooks file produced output: "
            f"stdout={unowned_stdout!r}, stderr={unowned_stderr!r}"
        )
    if calls:
        problems.append(f"unowned .claude/hooks file invoked Ruff: {calls!r}")

    assert not problems, "\n".join(problems)
