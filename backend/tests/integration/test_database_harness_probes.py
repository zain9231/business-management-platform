import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _run_probe(source: str, probe_path: Path) -> subprocess.CompletedProcess[str]:
    probe_path.write_text(source, encoding="utf-8", newline="\n")
    environment = os.environ.copy()
    test_database_url = environment.get("TEST_DATABASE_URL")
    if test_database_url is None or not test_database_url.strip():
        raise RuntimeError("TEST_DATABASE_URL must be set for subprocess probes")
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "-vv",
            "--verbosity=1",
            "-p",
            "tests.conftest",
            "-p",
            "no:cacheprovider",
            "--rootdir",
            str(BACKEND_ROOT),
            "--basetemp",
            str(probe_path.parent / "child-basetemp"),
            str(probe_path),
        ],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.mark.parametrize(("first", "second"), [("a", "b"), ("b", "a")])
def test_disabled_commit_cleanup_is_a_failing_negative_control(
    tmp_path: Path,
    first: str,
    second: str,
) -> None:
    result = _run_probe(
        f"""
from tests.conftest import CommittedProbe


def test_{first}(test_database_harness):
    probe = CommittedProbe(test_database_harness)
    assert probe.rows() == []
    probe.commit("negative-{first}", "cleanup deliberately disabled")


def test_{second}(test_database_harness):
    probe = CommittedProbe(test_database_harness)
    assert probe.rows() == []
    probe.commit("negative-{second}", "must not be reached")
""".lstrip(),
        tmp_path / f"test_negative_{first}_{second}.py",
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 1, combined
    assert "1 failed, 1 passed" in combined, combined
    assert f"negative-{first}" in combined, combined


def test_real_commit_cleanup_runs_after_a_deliberate_assertion_failure(tmp_path: Path) -> None:
    result = _run_probe(
        """
def test_deliberate_failure_after_commit(committed_probe):
    assert committed_probe.rows() == []
    committed_probe.commit("failure-path", "must be cleaned")
    raise AssertionError("deliberate failure after real commit")


def test_following_observer_starts_empty(committed_probe):
    assert committed_probe.rows() == []
""".lstrip(),
        tmp_path / "test_failure_cleanup.py",
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 1, combined
    assert "test_deliberate_failure_after_commit FAILED" in combined, combined
    assert "test_following_observer_starts_empty PASSED" in combined, combined
    assert "1 failed, 1 passed" in combined, combined
