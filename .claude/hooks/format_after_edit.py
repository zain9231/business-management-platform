#!/usr/bin/env python
"""PostToolUse: format and lint the file Claude just edited.

Silently does nothing when the toolchain for that file type is not installed yet, so this
hook is harmless before Phase 1 (P1-05) sets Ruff up and before P6-01 sets the frontend up.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import PurePosixPath

TIMEOUT = 45

SKIP_PREFIXES = ("docs/",)  # checksum-protected artifacts must never be reformatted


def rel_posix(raw: str, root: str) -> str | None:
    try:
        rel = os.path.relpath(os.path.abspath(raw), os.path.abspath(root))
    except (OSError, ValueError):
        return None
    if rel.startswith(os.pardir):
        return None
    return PurePosixPath(rel.replace(os.sep, "/")).as_posix()


def run(cmd: list[str], cwd: str) -> str | None:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, cwd=cwd)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        tail = (result.stdout + result.stderr).strip().splitlines()
        if tail:
            return "\n".join(tail[-25:])
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    raw = (payload.get("tool_input") or {}).get("file_path") or ""
    if not raw or not os.path.isfile(raw):
        return

    root = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    rel = rel_posix(raw, root)
    if not rel or rel.startswith(SKIP_PREFIXES):
        return

    messages: list[str] = []

    if rel.endswith(".py") and shutil.which("ruff"):
        run(["ruff", "format", raw], cwd=root)
        problem = run(["ruff", "check", "--fix", raw], cwd=root)
        if problem:
            messages.append(f"ruff check found issues it could not fix in {rel}:\n{problem}")

    elif rel.startswith("frontend/") and rel.endswith((".ts", ".tsx", ".css", ".json")):
        frontend = os.path.join(root, "frontend")
        if os.path.isdir(os.path.join(frontend, "node_modules")) and shutil.which("npx"):
            run(["npx", "--no-install", "prettier", "--write", raw], cwd=frontend)
            if rel.endswith((".ts", ".tsx")):
                problem = run(["npx", "--no-install", "eslint", "--fix", raw], cwd=frontend)
                if problem:
                    messages.append(f"eslint found issues it could not fix in {rel}:\n{problem}")

    if messages:
        print("\n\n".join(messages), file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
