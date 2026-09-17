import tomllib
from pathlib import Path
from typing import Any

PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _pyproject() -> dict[str, Any]:
    with PYPROJECT_PATH.open("rb") as source:
        return tomllib.load(source)


def test_required_markers_and_strict_modes_are_configured() -> None:
    project = _pyproject()
    pytest_options = project["tool"]["pytest"]["ini_options"]
    marker_names = {marker.split(":", 1)[0] for marker in pytest_options["markers"]}

    assert marker_names == {"unit", "integration", "concurrency", "dst", "deployment"}
    assert "--strict-markers" in pytest_options["addopts"]
    assert "--strict-config" in pytest_options["addopts"]


def test_pytest_cov_is_the_only_new_direct_test_dependency() -> None:
    project = _pyproject()
    dev_dependencies = project["project"]["optional-dependencies"]["dev"]

    assert "pytest-cov==7.1.0" in dev_dependencies
