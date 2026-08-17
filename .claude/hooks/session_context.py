#!/usr/bin/env python
"""SessionStart: print the current branch, working-tree state, and the next backlog task.

Keeps every session anchored to backlog order without spending context reading the 68 KB
backlog file.

Source of truth for "what's next" is `Next task: <id>` in docs/project/progress.md, because
implementation-backlog.md is checksum-protected and its checkboxes cannot be ticked freely.

`docs/project/progress.md` is authoritative for the current task. GitHub issues are authoritative for
in-flight work. `docs/project/implementation-backlog.md` supplies scope, sequence, dependencies,
acceptance criteria, and gates; its checkbox state is never a status source. If `progress.md` is
unreadable or absent, has a missing or duplicate `Next task:` line, has a task identifier that fails
the expected format, or names a task identifier not found in the backlog, stop: cannot determine
current task. Do not infer from backlog checkboxes.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

BACKLOG = os.path.join("docs", "project", "implementation-backlog.md")
PROGRESS = os.path.join("docs", "project", "progress.md")

NEXT_TASK_LINE = re.compile(r"^Next task:.*$", re.MULTILINE)
NEXT_TASK = re.compile(r"^Next task:\s*([A-Z][A-Z0-9]*-\d+)\s*$")
TASK_HEADING = re.compile(r"^###\s+([A-Z][A-Z0-9]*-\d+)\s*[—–-]\s*(.+?)\s*$")
PHASE_HEADING = re.compile(r"^##\s+((?:Phase\s|First deployment|MVP).*?)\s*$")
SITTING_SUFFIX = re.compile(r"\s*\([^()]*sitting[^()]*\)\s*$")


def git(args: list[str], cwd: str) -> str:
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=5, cwd=cwd)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def backlog_tasks(root: str) -> list[tuple[str, str, str]]:
    """Return every (phase, task-id, title) in backlog order."""
    tasks: list[tuple[str, str, str]] = []
    phase = ""
    for line in read(os.path.join(root, BACKLOG)).splitlines():
        phase_match = PHASE_HEADING.match(line)
        if phase_match:
            phase = phase_match.group(1)
            continue
        heading = TASK_HEADING.match(line)
        if heading:
            title = SITTING_SUFFIX.sub("", heading.group(2)).strip()
            tasks.append((phase, heading.group(1), title))
    return tasks


def completed_ids(progress: str) -> set[str]:
    """Task ids recorded under the Completed heading of progress.md."""
    body = re.split(r"^##\s+Completed\s*$", progress, maxsplit=1, flags=re.MULTILINE)
    if len(body) < 2:
        return set()
    body = re.split(r"^##\s+", body[1], maxsplit=1, flags=re.MULTILINE)[0]
    return set(re.findall(r"\b([A-Z][A-Z0-9]*-\d+)\b", body))


def status(root: str) -> tuple[str, str, str, int, int] | None:
    """Return (phase, task-id, title, done_in_phase, total_in_phase)."""
    tasks = backlog_tasks(root)
    if not tasks:
        return None

    progress = read(os.path.join(root, PROGRESS))
    next_task_lines = NEXT_TASK_LINE.findall(progress)
    if len(next_task_lines) != 1:
        return None
    match = NEXT_TASK.fullmatch(next_task_lines[0])
    if match is None:
        return None
    wanted = match.group(1)

    entry = next((t for t in tasks if t[1] == wanted), None)
    if entry is None:
        return None

    phase, task_id, title = entry
    in_phase = [t[1] for t in tasks if t[0] == phase]
    done = len(set(in_phase) & completed_ids(progress))
    return phase, task_id, title, done, len(in_phase)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        payload = {}

    root = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    branch = git(["rev-parse", "--abbrev-ref", "HEAD"], root) or "unknown"
    dirty = git(["status", "--porcelain"], root)
    changed = len([line for line in dirty.splitlines() if line.strip()])
    last = git(["log", "-1", "--pretty=%h %s"], root)

    lines = ["Repository state at session start:", f"- Branch: {branch}"]
    if branch == "main":
        lines.append("  main is protected — create a task branch before making any change.")
    lines.append(f"- Uncommitted changes: {changed} file(s)")
    if last:
        lines.append(f"- Last commit: {last}")

    current = status(root)
    if current:
        phase, task_id, title, done, total = current
        if total:
            lines.append(f"- {phase}: {done} of {total} tasks done")
        lines.append(f"- Next task: {task_id}" + (f" — {title}" if title else ""))
        lines.append(
            f"  Open it with /task-start {task_id}. Progress is tracked in "
            "docs/project/progress.md, not in the checksum-protected backlog."
        )
    else:
        lines.append("- cannot determine current task")

    print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
