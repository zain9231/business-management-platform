# Context budget hook — specification and reference implementation

Written 2026-08-17. Revision 2. Companion to `claude/claude-setup-guide.md` §6 and §7 in the
claude.ai Project.

Status: specified and tested, staged but not installed. Both files were delivered to
`context-budget-handoff/` in the repository root, because remote tooling is not permitted to write
into `.claude/`. §8 is the task prompt that moves them into place and finishes the install.

Revision 2 changes the thresholds from fractions of the context window to absolute token counts.
Revision 1 assumed a 200K window, which is wrong for this setup — see §3.

---

## 1. Problem

Nothing reminds you to `/clear`. Claude Code auto-compacts near the limit rather than telling you to
start fresh, `/context` reports only when asked, and the four installed hooks do not inspect session
length. `/clear` discipline is therefore unassisted memory.

The rejected alternative was an instruction — "start a new chat after 20 messages" — in `CLAUDE.md`
or the Project instructions. It fails on three counts. It requires the model to count turns, which
it does inconsistently; message count does not correlate with context use, since four turns that
read `bookings-api-contract.md` and the DBML cost more than twenty clarifications; and it occupies
lines that load on every request. §7 of the setup guide already resolves this class of problem:
something that must happen every time, regardless of judgment, is a hook, not an instruction.

**Decision.** A `UserPromptSubmit` hook measures real context use before each prompt and injects a
one-time notice per threshold. Zero cost until it fires, at most two notices per session.

---

## 2. What it measures

Not bytes, and not messages. The transcript JSONL records a `usage` block on each assistant entry.
The hook sums `input_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` and
`output_tokens` from the most recent main-thread assistant entry. Input plus cache is the prompt
that was actually sent; output is the part of it that carries into the next turn.

Three properties follow, and they are the reason for choosing this signal:

- It tracks real context use, so a session that reads three contracts crosses a threshold quickly
  and a session of short exchanges does not.
- It falls after a compaction, because the post-compact prompt genuinely is smaller. A byte count of
  the transcript grows monotonically and would keep firing after the problem was solved.
- Entries marked `isSidechain` are subagent turns describing a different context. The hook skips
  them, so the eight review subagents do not distort the main-thread measurement.

The trade-off is that `message.usage` and `isSidechain` are Claude Code transcript internals, not a
documented interface. If a future version renames them the hook finds no usage block and stays
silent. It degrades to doing nothing, never to firing wrongly. §4 is the calibration run that
confirms the format on this install before the hook is trusted.

---

## 3. Thresholds

**Absolute token counts, not fractions of the context window.** This environment is the reason.

Claude Code v2.1.233, Claude Pro, `opusplan`. On the Anthropic API Sonnet 5 always runs a 1M token
context window — there is no 200K variant, no `[1m]` suffix, and no usage credits required on any
plan — and sessions auto-compact at roughly 967K by default. Opus with 1M context does require usage
credits on Pro, so under `opusplan` the plan-mode turns likely run a 200K window while execution
turns run 1M. The effective window therefore changes within a single session.

Two consequences:

1. A percentage-of-window threshold is meaningless when the window moves mid-session, and at 1M it
   is useless anyway: 50% is 500K, which these sessions will never reach.
2. What degrades a long session at 300K is drift, stale file reads, and cost — none of which scale
   with the window size. Those are absolute quantities.

| Threshold | Default | Intent |
|---|---|---|
| 1 | 150,000 tokens | The useful one. Far enough in that clearing costs something, early enough that the session is still sharp. |
| 2 | 300,000 tokens | The session is now long by any measure. Finish the current task and clear rather than carry on. |

Set with `CONTEXT_BUDGET_TIERS`, a comma-separated list of token counts. `CONTEXT_BUDGET_WINDOW`
(default 1,000,000) affects only the percentage printed in the notice.

These defaults are estimates. §4 replaces them with numbers taken from real sessions.

---

## 4. Calibration

Report against the five most recent transcripts:

```powershell
Get-ChildItem "$env:USERPROFILE\.claude\projects" -Recurse -Filter *.jsonl |
  Sort-Object LastWriteTime -Descending | Select-Object -First 5 |
  ForEach-Object { python .claude\hooks\context_budget.py --report $_.FullName; "" }
```

Expected output shape:

```text
transcript: C:\Users\Zain\.claude\projects\...\<session-id>.jsonl
used:   334,000 tokens (33% of the 1M window)
tier 150K (150,000): REACHED
tier 300K (300,000): not reached
```

Reading the results:

- If most sessions peak well below 150K, lower threshold 1 until it would have fired on the sessions
  that actually felt long. A threshold that never fires is dead weight.
- If most sessions blow past 300K, both numbers are too low and the notice will be background noise.
- Pick threshold 1 near where a typical backlog task ends, and threshold 2 at roughly twice that.

`usage: NOT FOUND` means the transcript format on this install differs from §2. Stop and inspect one
transcript line before wiring the hook; do not install a hook that cannot measure. If the projects
directory is elsewhere, `/status` reports the real path.

### Calibration record

| Date | Session | Measurement | Outcome |
|---|---|---|---|
| 2026-08-17 | Install session (`chore/context-budget-hook`) | 91,835 tokens at completion — the full install: file moves, a settings merge, the calibration run, thirteen tests, one commit | Thresholds kept at 150,000 / 300,000. A complete task session costs roughly 92K, so 150K sits at ~1.6x a full task — a defensible line for "this session is now longer than the work it contains." 300K is unambiguously overdue for `/clear`. |

Only 4 transcripts existed at calibration time, not 5, and one had no assistant turn at all — a
session `/clear`'d immediately, not a format break. The hook stayed silent through the entire install
session, which is the behavior wanted: one task, no interruption.

Case 14 was closed by forcing `CONTEXT_BUDGET_TIERS=20000` on a resumed session (`claude --continue`)
rather than waiting for a session to reach 150K naturally.

---

## 5. Behavior

1. Runs on `UserPromptSubmit`, before Claude processes the prompt.
2. Reads the last 512 KB of the transcript only. Measured at 29 ms per invocation against a 3 MB
   transcript, interpreter start included.
3. Fires the highest crossed threshold that has not yet fired, and marks every lower threshold fired
   at the same time. A 150K notice arriving after a 300K one — which is what a post-compaction
   measurement produces — is noise.
4. Per-session state lives in `.claude/.cache/context-budget/<session_id>.json`, gitignored. Files
   older than three days are pruned whenever state is written, so the cache cannot grow.
5. `PostCompact` invokes the same script with `--reset`, clearing the thresholds. After a compaction
   the context cycle starts over and they should be able to fire again.
6. Every failure path exits 0 with no output: missing transcript, unparsable JSON, absent usage
   block, unwritable state directory, malformed `CONTEXT_BUDGET_TIERS`. The hook must never block or
   delay a prompt. It never uses exit code 2.
7. Plain stdout on `UserPromptSubmit` is added to context and shown in the transcript, so no JSON
   envelope is needed. The injected text is conditional — act only if this prompt starts different
   work, otherwise stay silent — so it does not become a recurring interruption mid-task.

### Injected text

```text
[context budget] This session has passed 150K tokens (~182,000, 18% of the 1M window). If this
prompt begins a different backlog task, a different contract, or unrelated work, stop and tell the
user to run /clear first — progress.md and the SessionStart hook will restore the context that
matters. If it continues the current task, ignore this notice and do not mention it.
```

The reference to `progress.md` and `session_context.py` is deliberate. Clearing is cheap precisely
because those two restore your position; the notice should say so at the moment you are deciding.

---

## 6. Installation

**Files.** `.claude/hooks/context_budget.py` (implementation in §9), alongside the four existing
hooks. This specification belongs at `.claude/context-budget-hook.md`, next to `.claude/README.md`,
because it documents Claude Code configuration rather than the platform. It is deliberately not in
`docs/project/`, which holds checksum-protected Phase 0 artifacts.

Both files currently sit in `context-budget-handoff/` at the repository root. Move them to the paths
above and delete that folder; it is a delivery staging area, not part of the layout.

**`.claude/settings.json`** — merge these entries, matching the command style of the four existing
hook entries:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/context_budget.py\"",
            "timeout": 5
          }
        ]
      }
    ],
    "PostCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/context_budget.py\" --reset",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

**`.gitignore`:** add `.claude/.cache/`.

The explicit 5-second timeout matters: the `UserPromptSubmit` default is 30 seconds, and a hook that
hangs delays every prompt you type.

**Note before editing `settings.json`:** the working tree had an uncommitted change to that file as
of 2026-08-17. Inspect it with `git diff .claude/settings.json` and commit or discard it before
merging these entries.

---

## 7. Verification

All thirteen cases below were executed against the reference implementation on 2026-08-17 and pass,
along with four configuration cases: custom `CONTEXT_BUDGET_TIERS`, a 200K `CONTEXT_BUDGET_WINDOW`
for display, a malformed tier list falling back to defaults, and the 3 MB timing measurement.
Re-run them after any edit. Cases 1–13 need only fabricated transcripts; case 14 is the live check.

1. Usage below threshold 1 produces no output and exit 0.
2. Usage above threshold 1 prints the notice once, with the correct token count.
3. The same session at the same usage on a later prompt prints nothing.
4. The same session crossing threshold 2 prints the threshold 2 notice.
5. The same session at threshold 2 on a later prompt prints nothing.
6. A session whose first measurement is already above threshold 2 fires threshold 2 only, not both.
7. After threshold 2 has fired, a lower measurement — the post-compaction case — prints nothing.
8. A transcript whose last entry is `isSidechain` measures the last main-thread entry instead.
9. A transcript with no usage block produces no output and exit 0.
10. A nonexistent transcript path produces no output and exit 0.
11. Malformed JSON on stdin produces no output and exit 0.
12. Empty stdin produces no output and exit 0.
13. `--reset` clears state, after which the crossed threshold fires again.
14. Installed live: a real session crossing threshold 1 shows the notice in the transcript, and the
    following prompt does not repeat it.

---

## 8. Task prompt for Claude Code

Run this in the repository, in a session cleared for the purpose.

> Install the context budget hook. Both files are staged in `context-budget-handoff/` at the
> repository root: `context-budget-hook.md` is the specification and `context_budget.py` is the
> implementation. Read the specification first and follow it exactly.
>
> 1. Move `context-budget-handoff/context-budget-hook.md` to `.claude/context-budget-hook.md` and
>    `context-budget-handoff/context_budget.py` to `.claude/hooks/context_budget.py`, then delete
>    the `context-budget-handoff/` folder.
> 2. Confirm the moved script matches §9 of the specification byte for byte. Report any difference
>    instead of silently correcting it.
> 3. Run `git diff .claude/settings.json` and show me the uncommitted change before touching that
>    file. Wait for my answer on whether to keep it.
> 4. Run the calibration in §4 against my five most recent transcripts and show me the raw output.
>    If any transcript reports `usage: NOT FOUND`, stop and show me one line of it instead.
> 5. Recommend threshold values from that data using the rules in §4, then **stop and wait for my
>    decision**. Do not proceed on your own numbers.
> 6. After I confirm the thresholds: set them as the default in `_tiers()` in the script, merge the
>    `UserPromptSubmit` and `PostCompact` entries from §6 into `.claude/settings.json` matching the
>    style of the four existing hook entries, and add `.claude/.cache/` to `.gitignore`.
> 7. Write verification cases 1–13 from §7 as a pytest module under `tests/hooks/`, generating the
>    fabricated transcripts as fixtures. Run them and show the results.
> 8. Commit on a branch as `chore: add context budget hook`. Do not merge.
>
> This is tooling, not platform code. It is outside the backlog, so do not touch `progress.md` and
> do not modify anything under `docs/`.

---

## 9. Reference implementation

```python
#!/usr/bin/env python3
"""Context budget nudge.

Hook events: UserPromptSubmit (measure and nudge), PostCompact (--reset).

Reads the real prompt token count from the last main-thread assistant message in
the session transcript and, once per threshold per session, injects a short
notice telling Claude to recommend /clear if this prompt starts different work.

Thresholds are absolute token counts, not fractions of the context window.
Sonnet 5 runs a 1M window and auto-compacts near 967K; what degrades a session
at 300K is drift, stale reads and cost, none of which scale with the window.

Design constraints:
  - Never blocks a prompt. Every failure path exits 0 with no output.
  - Costs zero tokens until a threshold is crossed; two notices per session max.
  - Reads only the tail of the transcript, so it stays fast on large sessions.

Configuration (environment):
  CONTEXT_BUDGET_TIERS    comma-separated token counts. Default "150000,300000"
  CONTEXT_BUDGET_WINDOW   context window, for the percentage shown in the
                          notice only. Default 1000000 (Sonnet 5)

Modes:
  (no args)  hook mode; reads the hook JSON payload on stdin
  --report   print the current measurement for calibration; accepts a
             transcript path as the next argument, or reads stdin payload
  --reset    clear this session's fired-threshold state (PostCompact)
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


def _tiers() -> tuple:
    raw = os.environ.get("CONTEXT_BUDGET_TIERS", "150000,300000")
    try:
        values = sorted({int(part.strip()) for part in raw.split(",") if part.strip()})
        return tuple(v for v in values if v > 0)
    except Exception:
        return (150_000, 300_000)


TIERS = _tiers()

# Display only. Sonnet 5 on the Anthropic API always runs a 1M window.
WINDOW = int(os.environ.get("CONTEXT_BUDGET_WINDOW", "1000000"))

# Bytes of transcript tail to scan for the most recent usage block.
TAIL_BYTES = 512 * 1024

STATE_DIR = Path(".claude") / ".cache" / "context-budget"
STATE_TTL_SECONDS = 3 * 24 * 60 * 60


def human(tokens: int) -> str:
    if tokens >= 1_000_000 and tokens % 1_000_000 == 0:
        return f"{tokens // 1_000_000}M"
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    if tokens >= 1_000:
        return f"{tokens // 1_000}K"
    return str(tokens)


def read_payload() -> dict:
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}


def state_path(session_id: str, cwd: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")[:64] or "unknown"
    return Path(cwd or ".") / STATE_DIR / f"{safe}.json"


def load_fired(path: Path) -> set:
    try:
        return set(json.loads(path.read_text(encoding="utf-8")).get("fired", []))
    except Exception:
        return set()


def save_fired(path: Path, fired: set) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"fired": sorted(fired)}), encoding="utf-8")
        prune(path.parent)
    except Exception:
        pass


def prune(directory: Path) -> None:
    """Delete state files older than the TTL so the cache cannot grow forever."""
    cutoff = time.time() - STATE_TTL_SECONDS
    try:
        for entry in directory.glob("*.json"):
            if entry.stat().st_mtime < cutoff:
                entry.unlink()
    except Exception:
        pass


def measure(transcript_path: str) -> int | None:
    """Return prompt tokens at the last main-thread assistant turn, or None.

    Sums input, cache-read, cache-creation and output tokens: input plus cache
    is the prompt that was actually sent, and output is the part of it that
    carries into the next turn. Sidechain entries are subagent turns whose usage
    describes a different context and must be skipped.
    """
    try:
        path = Path(transcript_path)
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > TAIL_BYTES:
                handle.seek(size - TAIL_BYTES)
            tail = handle.read()
    except Exception:
        return None

    for line in reversed(tail.decode("utf-8", errors="replace").splitlines()):
        line = line.strip()
        if not line or '"usage"' not in line:
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue  # truncated first line, or a non-JSON line
        if entry.get("isSidechain"):
            continue
        usage = (entry.get("message") or {}).get("usage") or entry.get("usage")
        if not isinstance(usage, dict):
            continue
        total = sum(
            int(usage.get(field) or 0)
            for field in (
                "input_tokens",
                "cache_read_input_tokens",
                "cache_creation_input_tokens",
                "output_tokens",
            )
        )
        if total > 0:
            return total
    return None


def notice(used: int, tier: int) -> str:
    share = f", {used / WINDOW:.0%} of the {human(WINDOW)} window" if WINDOW > 0 else ""
    return (
        f"[context budget] This session has passed {human(tier)} tokens "
        f"(~{used:,}{share}). "
        "If this prompt begins a different backlog task, a different contract, or "
        "unrelated work, stop and tell the user to run /clear first — progress.md "
        "and the SessionStart hook will restore the context that matters. "
        "If it continues the current task, ignore this notice and do not mention it."
    )


def main() -> int:
    args = sys.argv[1:]

    if args and args[0] == "--report":
        if len(args) > 1:
            transcript, used = args[1], measure(args[1])
        else:
            payload = read_payload()
            transcript = payload.get("transcript_path", "")
            used = measure(transcript)
        print(f"transcript: {transcript}")
        if used is None:
            print("usage: NOT FOUND — no parsable usage block in the transcript tail.")
            print("Check the transcript format before trusting the hook.")
            return 1
        print(f"used:   {used:,} tokens ({used / WINDOW:.0%} of the {human(WINDOW)} window)")
        for tier in TIERS:
            state = "REACHED" if used >= tier else "not reached"
            print(f"tier {human(tier)} ({tier:,}): {state}")
        return 0

    try:
        payload = read_payload()
    except Exception:
        return 0

    session_id = str(payload.get("session_id") or "")
    cwd = str(payload.get("cwd") or ".")
    path = state_path(session_id, cwd)

    if args and args[0] == "--reset":
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        return 0

    used = measure(str(payload.get("transcript_path") or ""))
    if used is None:
        return 0

    fired = load_fired(path)
    for tier in reversed(TIERS):
        if used >= tier and tier not in fired:
            # Mark every lower threshold fired as well. Measured usage falls
            # after a compaction, and a 150K notice arriving after a 300K one
            # would be noise.
            fired.update(t for t in TIERS if t <= tier)
            save_fired(path, fired)
            print(notice(used, tier))
            break
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # a context nudge must never break a prompt
```

---

## 10. What this does not do

It does not clear for you, and it should not. The decision needs the one input the hook cannot
have — whether the prompt you are about to send continues the current task. The hook supplies the
measurement; the convention supplies the rule.

**The convention: one backlog task, one session.** `/clear` at each task boundary. This costs almost
nothing because `session_context.py` prints the branch and next task at session start and
`progress.md` holds the live state. The hook exists for the case where you have already drifted past
a boundary without noticing.

A separate backstop worth setting: `/autocompact 300k`. Left alone, a Sonnet 5 session compacts at
roughly 967K, which discards an enormous amount of working context at once. At 300K a runaway
session compacts somewhere survivable. It is independent of this hook — the hook nudges you to
clear, autocompact decides what happens when you don't.

Decay triggers, in the form of §7 of the setup guide:

| Trigger | Action |
|---|---|
| The notice fires and you keep working every time | thresholds are too low; raise threshold 1 and re-run the calibration |
| You hit auto-compact without ever seeing threshold 2 | threshold 2 is too high, or the measurement broke — run `--report` |
| `usage: NOT FOUND` after a Claude Code upgrade | the transcript format changed; fix `measure()` or delete the hook |
| You never once acted on the notice after a month | delete the hook; an ignored nudge is pure cost |
