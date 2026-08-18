#!/usr/bin/env python
"""PreToolUse guard for Bash: enforce the protected-main pull-request workflow.

Blocks commits on main, direct pushes to main, force pushes, branch-protection bypasses,
and history rewrites. Fails open on any unexpected condition.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

PR_WORKFLOW = (
    "\n\nUse the documented workflow instead:\n"
    "  git switch -c <type>/<task-id>-<description>\n"
    "  git commit\n"
    "  git push -u origin <branch>\n"
    "  gh pr create --title \"<title>\" --body-file <reviewed-template-copy>\n"
    "  gh pr merge <number> --squash   (no --delete-branch; branch deletion is a separate step)\n"
    "See docs/project/git-operating-rules.md for the full canonical sequence."
)

# (compiled pattern, reason)
RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\bgit\s+push\b(?=[^\n]*\s(?:-f\b|--force\b|--force-with-lease\b))"),
        "BLOCKED: force push. It rewrites published history and can destroy the Phase 0 baseline.",
    ),
    (
        re.compile(r"\bgit\s+push\b[^\n]*\s(?:origin\s+)?(?:HEAD:)?main\b"),
        "BLOCKED: direct push to main. main is protected." + PR_WORKFLOW,
    ),
    (
        re.compile(r"\bgit\s+push\b[^\n]*\s--delete\b"),
        "BLOCKED: deleting a remote ref this way. See docs/project/git-operating-rules.md step c "
        "for the approved remote-branch-deletion command.",
    ),
    (
        re.compile(r"\bgit\s+(?:rebase|filter-branch|reset)\b[^\n]*\s(?:--hard\b|--root\b)|\bgit\s+filter-branch\b"),
        "BLOCKED: history rewrite. Ask the user first; this can invalidate the Phase 0 checksums and tag.",
    ),
    (
        re.compile(r"\bgit\s+clean\b[^\n]*\s-[a-zA-Z]*[xX]"),
        "BLOCKED: 'git clean -x' removes ignored files including .env and local database volumes.",
    ),
    (
        re.compile(r"enforce_admins"),
        "BLOCKED: disabling branch-protection admin enforcement. CONTRIBUTING.md permits this only "
        "as an emergency repair the user explicitly authorizes. Ask first, and restore it immediately after.",
    ),
    (
        re.compile(r"\bgh\s+pr\s+merge\b[^\n]*\s--admin\b"),
        "BLOCKED: '--admin' bypasses branch protection and required checks. Wait for CI.",
    ),
    (
        re.compile(r"\bgit\s+tag\b[^\n]*\s-d\b|\bgit\s+tag\b[^\n]*\s--delete\b"),
        "BLOCKED: deleting a tag. 'phase-0-complete' records the artifact manifest hash.",
    ),
    (
        re.compile(r"\brm\s+(?:-[a-zA-Z]*\s+)*-?[a-zA-Z]*[rR][a-zA-Z]*f|\brm\s+-[a-zA-Z]*f[a-zA-Z]*[rR]"),
        "BLOCKED: recursive force delete. Name the specific paths, or ask the user to run it.",
    ),
]


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


def current_branch(cwd: str | None) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command:
        return

    for pattern, reason in RULES:
        if pattern.search(command):
            deny(reason)

    # Committing on main, or pushing the current branch while it is main, is blocked.
    if re.search(r"\bgit\s+(commit|push)\b", command):
        branch = current_branch(payload.get("cwd"))
        if branch == "main":
            action = "commit on" if re.search(r"\bgit\s+commit\b", command) else "push from"
            deny(
                f"BLOCKED: {action} main. Every change belongs on a task branch." + PR_WORKFLOW
            )


if __name__ == "__main__":
    try:
        main()
    except Exception:  # never break the session over a guard
        pass
    sys.exit(0)
