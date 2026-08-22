"""Matcher-behavior tests for .claude/hooks/guard_git.py.

Drives the hook as a subprocess with a fabricated PreToolUse payload, the same way
test_context_budget.py drives context_budget.py. Every payload's cwd is a fresh
tmp_path with no git repository, so guard_git.current_branch() returns None and the
post-rules main-branch fallback stays inert -- these tests measure the RULES
matchers alone, independent of whatever branch the checkout is actually on.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "guard_git.py"


def run_guard(command: str, cwd: Path) -> dict | None:
    payload = json.dumps({"tool_input": {"command": command}, "cwd": str(cwd)})
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    if not result.stdout:
        return None
    return json.loads(result.stdout)


def assert_denied(command: str, cwd: Path) -> None:
    output = run_guard(command, cwd)
    assert output is not None, f"expected a denial for: {command!r}"
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"


def assert_allowed(command: str, cwd: Path) -> None:
    output = run_guard(command, cwd)
    assert output is None, f"expected no denial for: {command!r}, got {output!r}"


ENFORCE_ADMINS_URL = "repos/o/r/branches/main/protection/enforce_admins"

DELETE_SPELLINGS = {
    "method-delete": f'gh api --method DELETE "{ENFORCE_ADMINS_URL}"',
    "method-eq-delete": f'gh api --method=DELETE "{ENFORCE_ADMINS_URL}"',
    "dash-x-delete": f'gh api -X DELETE "{ENFORCE_ADMINS_URL}"',
    "dash-xdelete": f'gh api -XDELETE "{ENFORCE_ADMINS_URL}"',
}

MULTILINE_AND_INDIRECT_DELETE_FORMS = {
    "target-first-continuation": (
        f'gh api "{ENFORCE_ADMINS_URL}" \\\n  --method DELETE'
    ),
    "method-first-continuation": (
        f'gh api \\\n  --method DELETE \\\n  "{ENFORCE_ADMINS_URL}"'
    ),
    "no-leading-whitespace": f'-XDELETE "{ENFORCE_ADMINS_URL}"',
    "variable-indirection": (
        f'REF="{ENFORCE_ADMINS_URL}"; gh api --method DELETE "$REF"'
    ),
}

MENTION_DOES_NOT_EXEMPT_OTHER_MATCHERS = {
    "force-push": 'git push --force origin main  # not an enforce_admins call',
    "history-rewrite": 'git rebase --root  # see enforce_admins docs for the emergency case',
    "recursive-delete": "rm -rf /tmp/enforce_admins-notes",
}

PRESERVED_MATCHERS = {
    "force-push": "git push --force origin main",
    "direct-push-to-main": "git push origin main",
    "push-delete": "git push origin --delete old-branch",
    "history-rewrite": "git rebase --root",
    "clean-x": "git clean -xdf",
    "pr-merge-admin": "gh pr merge 42 --admin",
    "tag-deletion": "git tag -d phase-0-complete",
    "recursive-force-delete": "rm -rf /tmp/scratch",
}


@pytest.mark.parametrize("command", DELETE_SPELLINGS.values(), ids=list(DELETE_SPELLINGS))
def test_enforce_admins_delete_spellings_stay_denied(command, tmp_path):
    assert_denied(command, tmp_path)


@pytest.mark.parametrize(
    "command",
    MULTILINE_AND_INDIRECT_DELETE_FORMS.values(),
    ids=list(MULTILINE_AND_INDIRECT_DELETE_FORMS),
)
def test_enforce_admins_multiline_and_indirect_delete_forms_stay_denied(command, tmp_path):
    assert_denied(command, tmp_path)


def test_enforce_admins_method_post_restore_is_allowed(tmp_path):
    assert_allowed(f'gh api --method POST "{ENFORCE_ADMINS_URL}"', tmp_path)


def test_enforce_admins_no_method_flag_is_allowed(tmp_path):
    assert_allowed(f'gh api "{ENFORCE_ADMINS_URL}"', tmp_path)


def test_enforce_admins_incidental_mention_is_allowed(tmp_path):
    assert_allowed(
        'echo "CONTRIBUTING.md documents the enforce_admins bypass pair"', tmp_path
    )


@pytest.mark.parametrize(
    "command",
    MENTION_DOES_NOT_EXEMPT_OTHER_MATCHERS.values(),
    ids=list(MENTION_DOES_NOT_EXEMPT_OTHER_MATCHERS),
)
def test_enforce_admins_mention_does_not_exempt_other_matchers(command, tmp_path):
    assert_denied(command, tmp_path)


@pytest.mark.parametrize("command", PRESERVED_MATCHERS.values(), ids=list(PRESERVED_MATCHERS))
def test_other_matchers_remain_effective(command, tmp_path):
    assert_denied(command, tmp_path)


def test_ordinary_command_produces_no_denial(tmp_path):
    assert_allowed("git status", tmp_path)
