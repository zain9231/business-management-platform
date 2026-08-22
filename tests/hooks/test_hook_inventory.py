"""Tests for .claude/README.md's hooks inventory against .claude/settings.json.

Two independent functions, no shared aborting fixture: a mismatch in the table
must not prevent the prose-count defect from being demonstrated on its own, and
a mismatch in the prose count must not prevent the table defect from being
demonstrated on its own.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
README = REPO_ROOT / ".claude" / "README.md"

COMMAND_SCRIPT_RE = re.compile(r'([A-Za-z0-9_]+\.py)"?\s*(.*)$')
HOOKS_HEADING_RE = re.compile(r"^## Hooks\s*$", re.MULTILINE)
NEXT_HEADING_RE = re.compile(r"^## ", re.MULTILINE)
BACKTICK_RE = re.compile(r"`([^`]+)`")
PROSE_COUNT_RE = re.compile(r"in the (\w+) `command` entries")
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _normalize_command(raw_command: str) -> str:
    match = COMMAND_SCRIPT_RE.search(raw_command)
    assert match, f"could not find a *.py script in hook command: {raw_command!r}"
    script, trailing = match.groups()
    return f"{script} {trailing.strip()}".strip()


def _settings_hooks() -> list[dict]:
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    return [
        hook
        for groups in data["hooks"].values()
        for group in groups
        for hook in group.get("hooks", [])
        if hook.get("type") == "command"
    ]


def _settings_rows() -> list[tuple[str, str]]:
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    rows: list[tuple[str, str]] = []
    for event, groups in data["hooks"].items():
        for group in groups:
            for hook in group.get("hooks", []):
                if hook.get("type") == "command":
                    rows.append((event, _normalize_command(hook["command"])))
    return rows


def _hooks_table_section() -> str:
    text = README.read_text(encoding="utf-8")
    start = HOOKS_HEADING_RE.search(text)
    assert start, "'.claude/README.md' has no '## Hooks' heading"
    rest = text[start.end() :]
    end = NEXT_HEADING_RE.search(rest)
    return rest[: end.start()] if end else rest


def _readme_hook_rows() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in _hooks_table_section().splitlines():
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 3:
            continue
        event_cell, script_cell, _effect_cell = cells
        if event_cell in {"", "Event"} or set(event_cell) <= set("-: "):
            continue
        event_match = BACKTICK_RE.search(event_cell)
        script_match = BACKTICK_RE.search(script_cell)
        assert event_match and script_match, f"unparsable hooks-table row: {line!r}"
        rows.append((event_match.group(1), script_match.group(1)))
    return rows


def test_readme_hooks_table_matches_settings_inventory():
    assert sorted(_readme_hook_rows()) == sorted(_settings_rows())


def test_readme_prose_command_count_matches_settings():
    text = README.read_text(encoding="utf-8")
    match = PROSE_COUNT_RE.search(text)
    assert match, "could not find the Linux/WSL command-count sentence in '.claude/README.md'"
    word = match.group(1).lower()
    stated = int(word) if word.isdigit() else NUMBER_WORDS.get(word)
    assert stated is not None, f"unrecognized count word: {word!r}"
    assert stated == len(_settings_hooks())
