"""Repository-tooling inventory contracts.

The hook tests compare .claude/README.md with .claude/settings.json. They remain
independent so either mismatch is demonstrated even if the other assertion
fails. The hierarchy test reads only the rendered target tree in
docs/project/file-structure.md and proves P1-05's new tooling paths are admitted
before those files are created.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
README = REPO_ROOT / ".claude" / "README.md"
FILE_STRUCTURE = REPO_ROOT / "docs" / "project" / "file-structure.md"

COMMAND_SCRIPT_RE = re.compile(r'([A-Za-z0-9_]+\.py)"?\s*(.*)$')
HOOKS_HEADING_RE = re.compile(r"^## Hooks\s*$", re.MULTILINE)
NEXT_HEADING_RE = re.compile(r"^## ", re.MULTILINE)
BACKTICK_RE = re.compile(r"`([^`]+)`")
PROSE_COUNT_RE = re.compile(r"in the (\w+) `command` entries")
CANONICAL_TREE_RE = re.compile(
    r"^## 2\. Canonical repository hierarchy\s*$\n\n"
    r"```text\n(?P<tree>.*?)\n```$",
    re.MULTILINE | re.DOTALL,
)
TREE_ENTRY_RE = re.compile(r"^(?P<indent>(?:│   |    )*)(?:├── |└── )(?P<name>.+)$")
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


def _settings_hooks() -> list[dict[str, object]]:
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


def _canonical_tree_paths() -> set[str]:
    text = FILE_STRUCTURE.read_text(encoding="utf-8")
    tree_match = CANONICAL_TREE_RE.search(text)
    assert tree_match, "could not find canonical hierarchy tree in 'file-structure.md'"

    paths: set[str] = set()
    parents: list[str] = []
    for line in tree_match.group("tree").splitlines():
        entry = TREE_ENTRY_RE.match(line)
        if not entry:
            continue
        indent = entry.group("indent")
        depth = len(indent) // 4
        assert depth <= len(parents), f"invalid canonical hierarchy indentation: {line!r}"

        raw_name = entry.group("name")
        name = raw_name.removesuffix("/")
        parents = parents[:depth]
        paths.add("/".join([*parents, name]))
        if raw_name.endswith("/"):
            parents.append(name)

    return paths


def test_readme_hooks_table_matches_settings_inventory() -> None:
    assert sorted(_readme_hook_rows()) == sorted(_settings_rows())


def test_readme_prose_command_count_matches_settings() -> None:
    text = README.read_text(encoding="utf-8")
    match = PROSE_COUNT_RE.search(text)
    assert match, "could not find the Linux/WSL command-count sentence in '.claude/README.md'"
    word = match.group(1).lower()
    stated = int(word) if word.isdigit() else NUMBER_WORDS.get(word)
    assert stated is not None, f"unrecognized count word: {word!r}"
    assert stated == len(_settings_hooks())


def test_canonical_hierarchy_admits_p1_05_quality_paths() -> None:
    required = {
        "frontend/.prettierignore",
        "frontend/.prettierrc.json",
        "frontend/eslint.config.mjs",
        "scripts/quality.py",
        "tests/hooks/test_quality_tooling.py",
    }
    missing = required - _canonical_tree_paths()
    assert not missing, f"canonical hierarchy is missing P1-05 paths: {sorted(missing)}"


def test_application_settings_construction_is_confined_to_configuration_module() -> None:
    allowed = REPO_ROOT / "backend" / "app" / "core" / "config.py"
    violations: list[str] = []
    for directory, children, files in REPO_ROOT.walk():
        children[:] = [
            name
            for name in children
            if not name.startswith(".")
            and name
            not in {
                "tests",
                "tmp",
                "temp",
                "node_modules",
                "venv",
                "env",
                "build",
                "dist",
                "__pycache__",
            }
        ]
        for filename in files:
            path = directory / filename
            if path.suffix != ".py" or path == allowed:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            names = {"Settings"}
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    names.update(
                        alias.asname or alias.name
                        for alias in node.names
                        if alias.name == "Settings"
                    )
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                function = node.func
                if (
                    isinstance(function, ast.Name)
                    and function.id in names
                    or isinstance(function, ast.Attribute)
                    and function.attr == "Settings"
                ):
                    violations.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
    assert not violations, f"Use load_settings() instead of direct construction: {violations}"


def test_configuration_value_error_messages_are_string_literals() -> None:
    path = REPO_ROOT / "backend" / "app" / "core" / "config.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "ValueError"
    ]
    assert calls, "Expected configuration validators raising ValueError"
    violations = [
        call.lineno
        for call in calls
        if not (
            len(call.args) == 1
            and not call.keywords
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        )
    ]
    assert not violations, (
        f"Configuration ValueError messages must be string literals: {violations}"
    )
