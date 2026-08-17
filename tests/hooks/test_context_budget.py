"""Verification cases 1-13 for .claude/hooks/context_budget.py, per
.claude/context-budget-hook.md §7.

Each case runs the hook script as a real subprocess against a fabricated
transcript, so the fired-threshold state file and the transcript-tail
scanner are both exercised exactly as they run under Claude Code.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "context_budget.py"
TIER_1 = 150_000
TIER_2 = 300_000


def usage_entry(tokens: int, is_sidechain: bool = False) -> str:
    return json.dumps(
        {
            "type": "assistant",
            "isSidechain": is_sidechain,
            "message": {
                "usage": {
                    "input_tokens": tokens,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "output_tokens": 0,
                }
            },
        }
    )


def write_transcript(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_hook(cwd: Path, session_id: str, transcript_path, args=None, raw_stdin=None):
    payload = {
        "session_id": session_id,
        "cwd": str(cwd),
        "transcript_path": str(transcript_path) if transcript_path is not None else "",
    }
    stdin_data = raw_stdin if raw_stdin is not None else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(args or [])],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=10,
    )


def state_file(cwd: Path, session_id: str) -> Path:
    return cwd / ".claude" / ".cache" / "context-budget" / f"{session_id}.json"


def test_case_01_below_threshold_produces_no_output(tmp_path):
    transcript = write_transcript(tmp_path / "t.jsonl", [usage_entry(50_000)])
    result = run_hook(tmp_path, "case01", transcript)
    assert result.returncode == 0
    assert result.stdout == ""


def test_case_02_crossing_threshold_1_prints_notice_once(tmp_path):
    transcript = write_transcript(tmp_path / "t.jsonl", [usage_entry(200_000)])
    result = run_hook(tmp_path, "case02", transcript)
    assert result.returncode == 0
    assert result.stdout.count("[context budget]") == 1
    assert "150K" in result.stdout
    assert "200,000" in result.stdout


def test_case_03_same_usage_on_later_prompt_prints_nothing(tmp_path):
    transcript = write_transcript(tmp_path / "t.jsonl", [usage_entry(200_000)])
    first = run_hook(tmp_path, "case03", transcript)
    second = run_hook(tmp_path, "case03", transcript)
    assert "[context budget]" in first.stdout
    assert second.returncode == 0
    assert second.stdout == ""


def test_case_04_crossing_threshold_2_prints_threshold_2_notice(tmp_path):
    t1 = write_transcript(tmp_path / "t1.jsonl", [usage_entry(200_000)])
    t2 = write_transcript(tmp_path / "t2.jsonl", [usage_entry(350_000)])
    run_hook(tmp_path, "case04", t1)
    second = run_hook(tmp_path, "case04", t2)
    assert second.returncode == 0
    assert second.stdout.count("[context budget]") == 1
    assert "300K" in second.stdout
    assert "350,000" in second.stdout


def test_case_05_same_usage_at_threshold_2_on_later_prompt_prints_nothing(tmp_path):
    t1 = write_transcript(tmp_path / "t1.jsonl", [usage_entry(200_000)])
    t2 = write_transcript(tmp_path / "t2.jsonl", [usage_entry(350_000)])
    run_hook(tmp_path, "case05", t1)
    run_hook(tmp_path, "case05", t2)
    third = run_hook(tmp_path, "case05", t2)
    assert third.returncode == 0
    assert third.stdout == ""


def test_case_06_first_measurement_above_threshold_2_fires_only_threshold_2(tmp_path):
    transcript = write_transcript(tmp_path / "t.jsonl", [usage_entry(500_000)])
    result = run_hook(tmp_path, "case06", transcript)
    assert result.returncode == 0
    assert result.stdout.count("[context budget]") == 1
    assert "300K" in result.stdout
    assert "150K" not in result.stdout


def test_case_07_lower_measurement_after_threshold_2_fired_prints_nothing(tmp_path):
    high = write_transcript(tmp_path / "high.jsonl", [usage_entry(500_000)])
    low = write_transcript(tmp_path / "low.jsonl", [usage_entry(80_000)])
    run_hook(tmp_path, "case07", high)
    second = run_hook(tmp_path, "case07", low)
    assert second.returncode == 0
    assert second.stdout == ""


def test_case_08_sidechain_last_entry_measures_main_thread_entry_instead(tmp_path):
    transcript = write_transcript(
        tmp_path / "t.jsonl",
        [usage_entry(200_000, is_sidechain=False), usage_entry(900_000, is_sidechain=True)],
    )
    result = run_hook(tmp_path, "case08", transcript)
    assert result.returncode == 0
    assert "200,000" in result.stdout
    assert "900,000" not in result.stdout
    assert "150K" in result.stdout


def test_case_09_no_usage_block_produces_no_output(tmp_path):
    transcript = write_transcript(
        tmp_path / "t.jsonl",
        [json.dumps({"type": "user", "message": {"content": "hello"}})],
    )
    result = run_hook(tmp_path, "case09", transcript)
    assert result.returncode == 0
    assert result.stdout == ""


def test_case_10_nonexistent_transcript_path_produces_no_output(tmp_path):
    result = run_hook(tmp_path, "case10", tmp_path / "does-not-exist.jsonl")
    assert result.returncode == 0
    assert result.stdout == ""


def test_case_11_malformed_json_on_stdin_produces_no_output():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input="{not valid json",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout == ""


def test_case_12_empty_stdin_produces_no_output():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input="",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout == ""


def test_case_13_reset_clears_state_and_threshold_fires_again(tmp_path):
    transcript = write_transcript(tmp_path / "t.jsonl", [usage_entry(200_000)])

    first = run_hook(tmp_path, "case13", transcript)
    assert "[context budget]" in first.stdout
    assert state_file(tmp_path, "case13").exists()

    reset = run_hook(tmp_path, "case13", transcript, args=["--reset"])
    assert reset.returncode == 0
    assert reset.stdout == ""
    assert not state_file(tmp_path, "case13").exists()

    third = run_hook(tmp_path, "case13", transcript)
    assert third.returncode == 0
    assert "[context budget]" in third.stdout
    assert "150K" in third.stdout
