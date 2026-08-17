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
