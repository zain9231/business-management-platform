import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = BACKEND_ROOT / "pyproject.toml"


def _run_pytest(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-vv", *arguments],
        cwd=BACKEND_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_unknown_marker_is_rejected_by_an_isolated_pytest_probe(tmp_path: Path) -> None:
    probe = tmp_path / "test_unknown_marker.py"
    probe.write_text(
        "import pytest\n\n@pytest.mark.not_registered\ndef test_probe():\n    pass\n",
        encoding="utf-8",
        newline="\n",
    )

    result = _run_pytest(
        "-p",
        "no:cacheprovider",
        "--strict-markers",
        "-c",
        str(PYPROJECT),
        str(probe),
    )

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "'not_registered' not found in `markers` configuration option" in combined


def test_unknown_config_is_rejected_by_an_isolated_pytest_probe(tmp_path: Path) -> None:
    probe = tmp_path / "test_valid.py"
    config = tmp_path / "pytest.ini"
    probe.write_text("def test_probe():\n    pass\n", encoding="utf-8", newline="\n")
    config.write_text(
        "[pytest]\naddopts = --strict-config\nunknown_p106_option = true\n",
        encoding="utf-8",
        newline="\n",
    )

    result = _run_pytest("-p", "no:cacheprovider", "-c", str(config), str(probe))

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Unknown config option: unknown_p106_option" in combined


def test_frozen_clock_restores_after_an_isolated_failure(tmp_path: Path) -> None:
    probe = tmp_path / "test_clock_failure.py"
    probe.write_text(
        """
from datetime import UTC, datetime

from app.core import clock

CHOSEN = datetime(2001, 2, 3, 4, 5, tzinfo=UTC)


def test_deliberate_failure(frozen_time):
    with frozen_time(CHOSEN):
        assert clock.utc_now() == CHOSEN
        raise AssertionError("deliberate clock probe failure")


def test_clock_is_restored_after_failure():
    assert clock.utc_now() != CHOSEN
""".lstrip(),
        encoding="utf-8",
        newline="\n",
    )

    result = _run_pytest(
        "-p",
        "tests.conftest",
        "-p",
        "no:cacheprovider",
        "-c",
        str(PYPROJECT),
        str(probe),
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 1
    assert "test_deliberate_failure" in combined
    assert "test_clock_is_restored_after_failure" in combined
    assert "1 failed, 1 passed" in combined
