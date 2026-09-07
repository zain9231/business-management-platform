"""Cross-platform quality commands for repository-owned Python."""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
PYTHON_TARGETS = ("app", "tests", "../tests", "../scripts/quality.py")
COMMANDS = ("format", "lint", "typecheck")
MISSING_TOOL_EXIT_STATUS = 127
LAUNCH_ERROR_EXIT_STATUS = 126
FRONTEND_DEFERRAL = "Frontend format and lint are deferred to P6-01; no frontend command was run."

FORMAT_STEPS = (
    ("check", "--fix", "--no-cache", *PYTHON_TARGETS),
    ("format", "--no-cache", *PYTHON_TARGETS),
)
LINT_STEPS = (
    ("format", "--check", "--no-cache", *PYTHON_TARGETS),
    ("check", "--no-cache", *PYTHON_TARGETS),
)
TYPECHECK_STEPS = (("--cache-dir", os.devnull),)


def _tool_available(tool: str) -> bool:
    try:
        return importlib.util.find_spec(tool) is not None
    except (ImportError, ValueError):
        return False


def _child_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["MYPY_CACHE_DIR"] = os.devnull
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _run_tool(tool: str, steps: tuple[tuple[str, ...], ...]) -> int:
    if not _tool_available(tool):
        print(
            f"quality: required tool '{tool}' is unavailable. "
            "Install the backend development dependencies from repository root, then retry: "
            'python -m pip install -e "backend[dev]"',
            file=sys.stderr,
        )
        return MISSING_TOOL_EXIT_STATUS

    environment = _child_environment()
    for arguments in steps:
        command = [sys.executable, "-m", tool, *arguments]
        try:
            result = subprocess.run(
                command,
                cwd=BACKEND_ROOT,
                env=environment,
                check=False,
                shell=False,
            )
        except OSError as error:
            print(f"quality: could not launch '{tool}': {error}", file=sys.stderr)
            return LAUNCH_ERROR_EXIT_STATUS
        if result.returncode != 0:
            return result.returncode
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/quality.py",
        description="Run repository-owned Python quality commands.",
    )
    parser.add_argument("command", choices=COMMANDS)
    command = str(parser.parse_args(argv).command)

    if command in {"format", "lint"}:
        print(FRONTEND_DEFERRAL, file=sys.stderr)

    if command == "format":
        return _run_tool("ruff", FORMAT_STEPS)
    if command == "lint":
        return _run_tool("ruff", LINT_STEPS)
    return _run_tool("mypy", TYPECHECK_STEPS)


if __name__ == "__main__":
    raise SystemExit(main())
