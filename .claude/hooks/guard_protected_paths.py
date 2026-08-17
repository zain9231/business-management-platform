#!/usr/bin/env python
"""PreToolUse guard: block writes to checksum-protected artifacts and secret files.

Reads the hook payload on stdin and emits a PreToolUse permission decision on stdout.
Fails open: any unexpected condition exits 0 without a decision.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import PurePosixPath

# The ten Phase 0 artifacts covered by docs/project/phase-0-artifacts.sha256,
# plus the manifest itself. Editing any of these breaks the phase-0-complete tag.
PROTECTED = {
    "docs/project/master-specification-v1.2.docx",
    "docs/project/implementation-backlog.md",
    "docs/api/shared-api-conventions.md",
    "docs/api/contracts/authentication-api-contract.md",
    "docs/api/contracts/customers-api-contract.md",
    "docs/api/contracts/staff-api-contract.md",
    "docs/api/contracts/services-api-contract.md",
    "docs/api/contracts/bookings-api-contract.md",
    "docs/architecture/erd/source/business-management-platform-erd-v1.2.dbml",
    "docs/architecture/erd/exports/business-management-platform-erd-v1.2.pdf",
    "docs/project/phase-0-artifacts.sha256",
}

SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")


def deny(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def relative_path(raw: str, project_dir: str) -> str | None:
    """Return the repo-relative POSIX path, or None if outside the project."""
    try:
        target = os.path.realpath(os.path.abspath(raw))
        root = os.path.realpath(os.path.abspath(project_dir))
        rel = os.path.relpath(target, root)
    except (OSError, ValueError):
        return None
    if rel.startswith(os.pardir):
        return None
    return PurePosixPath(rel.replace(os.sep, "/")).as_posix()


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    tool_input = payload.get("tool_input") or {}
    raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not raw:
        return

    project_dir = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    rel = relative_path(raw, project_dir)
    name = os.path.basename(raw)

    if rel and rel in PROTECTED:
        deny(
            f"BLOCKED: '{rel}' is one of the checksum-protected Phase 0 artifacts covered by "
            "docs/project/phase-0-artifacts.sha256. Editing it breaks the manifest and the "
            "phase-0-complete tag.\n\n"
            "If this edit is genuinely required (a Decision Log entry, an accepted contract "
            "revision, or ticking a completed backlog item):\n"
            "  1. Stop and tell the user exactly what must change and why.\n"
            "  2. Get an explicit go-ahead.\n"
            "  3. Recompute docs/project/phase-0-artifacts.sha256 and report the new manifest hash.\n"
            "  4. Commit it alone as a docs: change, never bundled with implementation.\n"
            "See .claude/rules/frozen-artifacts.md and the /decision-log skill."
        )

    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        deny(
            f"BLOCKED: '{name}' holds real secrets and is gitignored. Edit .env.example with "
            "placeholder values instead, and document the setting in the README."
        )

    if name.lower().endswith(SECRET_SUFFIXES):
        deny(f"BLOCKED: '{name}' looks like a private key or certificate. Never write one into the repository.")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # never break the session over a guard
        pass
    sys.exit(0)
