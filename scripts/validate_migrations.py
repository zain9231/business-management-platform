"""Validate the repository's pre-P2-01 migration invariant."""

from __future__ import annotations

import ast
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATHS = (Path("backend/alembic.ini"), Path("backend/alembic"))
TRANSITION_MESSAGE = (
    "P2-01 transition required: replace this negative invariant with PostgreSQL upgrade, "
    "downgrade, clean replay, and drift checks when the migration surface is introduced."
)


def _tracked_python_files(repository_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(repository_root), "ls-files", "--", "*.py"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "git ls-files failed"
        raise RuntimeError(detail)
    return [repository_root / line for line in result.stdout.splitlines() if line]


def _migration_markers(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError) as error:
        return [f"could not inspect tracked Python file {path}: {error}"]

    markers: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            alias.name == "alembic" or alias.name.startswith("alembic.") for alias in node.names
        ):
            markers.append("imports alembic")
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and (node.module == "alembic" or node.module.startswith("alembic."))
        ):
            markers.append("imports from alembic")
        elif (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "revision" for target in node.targets
            )
            or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "revision"
            )
        ):
            markers.append("defines a migration revision")
    return markers


def validate_repository(
    repository_root: Path,
    *,
    tracked_python_files: Sequence[Path] | None = None,
) -> list[str]:
    """Return violations of the current no-migration-surface contract."""

    errors = [
        f"unexpected migration surface exists: {relative.as_posix()}"
        for relative in MIGRATION_PATHS
        if (repository_root / relative).exists()
    ]
    inspected_files = (
        list(tracked_python_files)
        if tracked_python_files is not None
        else _tracked_python_files(repository_root)
    )
    for path in inspected_files:
        for marker in _migration_markers(path):
            try:
                relative = path.relative_to(repository_root).as_posix()
            except ValueError:
                relative = str(path)
            errors.append(f"{relative}: {marker}")
    return errors


def main() -> int:
    try:
        errors = validate_repository(REPOSITORY_ROOT)
    except RuntimeError as inspection_error:
        print(
            f"migration validation could not inspect tracked files: {inspection_error}",
            file=sys.stderr,
        )
        return 2

    if errors:
        print("Pre-P2-01 migration invariant failed:", file=sys.stderr)
        for violation in errors:
            print(f"- {violation}", file=sys.stderr)
        print(TRANSITION_MESSAGE, file=sys.stderr)
        return 1

    print("Migration validation passed: no pre-P2-01 migration surface is present.")
    print(TRANSITION_MESSAGE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
