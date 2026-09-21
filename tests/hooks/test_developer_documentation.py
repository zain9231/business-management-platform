"""Contract tests for the P1-08 developer documentation."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ROOT_README = REPOSITORY_ROOT / "README.md"
BACKEND_README = REPOSITORY_ROOT / "backend" / "README.md"
LOCAL_DEVELOPMENT = REPOSITORY_ROOT / "docs" / "deployment" / "local-development.md"
DOCKERFILE = REPOSITORY_ROOT / "backend" / "Dockerfile"

DBML_TARGET = "docs/architecture/erd/source/business-management-platform-erd-v1.2.dbml"
CONTRACTS_TARGET = "docs/api/contracts/"
LAYOUT_TARGET = "docs/project/file-structure.md"


def _text(path: Path) -> str:
    assert path.is_file(), f"required documentation file is missing: {path}"
    return path.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    level = len(heading) - len(heading.lstrip("#"))
    pattern = re.compile(rf"(?ms)^{re.escape(heading)}\n(?P<body>.*?)(?=^#{{1,{level}}} |\Z)")
    match = pattern.search(text)
    assert match is not None, f"required section is missing: {heading}"
    return match.group("body")


def _fenced_blocks(text: str) -> list[tuple[str, str]]:
    return [
        (match.group("language"), match.group("body"))
        for match in re.finditer(
            r"(?ms)^```(?P<language>[^\n]*)\n(?P<body>.*?)^```$",
            text,
        )
    ]


def _link_targets(text: str) -> set[str]:
    return set(re.findall(r"\[[^\]]+\]\(([^)]+)\)", text))


@pytest.mark.parametrize(
    ("path", "required_tokens"),
    [
        (ROOT_README, ("POSTGRES_PORT", "BACKEND_PORT", "TEST_DATABASE_URL")),
        (BACKEND_README, ("POSTGRES_PORT", "BACKEND_PORT", "TEST_DATABASE_URL")),
        (LOCAL_DEVELOPMENT, ("POSTGRES_PORT", "BACKEND_PORT")),
    ],
    ids=("root-readme", "backend-readme", "local-development"),
)
def test_documented_commands_are_parameterized(
    path: Path, required_tokens: tuple[str, ...]
) -> None:
    fenced_text = "\n".join(body for _, body in _fenced_blocks(_text(path)))
    missing = [token for token in required_tokens if token not in fenced_text]
    assert not missing, (
        f"fenced commands in {path.relative_to(REPOSITORY_ROOT)} lack parameters: {missing}"
    )


@pytest.mark.parametrize(
    "path",
    [ROOT_README, BACKEND_README, LOCAL_DEVELOPMENT],
    ids=("root-readme", "backend-readme", "local-development"),
)
def test_documented_commands_do_not_pin_loopback_ports(path: Path) -> None:
    fenced_text = "\n".join(body for _, body in _fenced_blocks(_text(path)))
    pinned_ports = re.findall(
        r"(?i)(?:127\.0\.0\.1|localhost):(?:8000|5432)\b",
        fenced_text,
    )

    assert not pinned_ports, (
        f"fenced commands in {path.relative_to(REPOSITORY_ROOT)} pin loopback ports: {pinned_ports}"
    )


def test_backend_liveness_body_matches_the_endpoint_contract() -> None:
    text = _text(BACKEND_README)

    assert '`{"status":"live"}`' in text
    assert '`{"status": "live"}`' not in text


def test_ci_equivalent_section_declares_its_shell_platforms() -> None:
    section = _section(_text(ROOT_README), "### CI-equivalent checks")
    languages = [language for language, _ in _fenced_blocks(section)]

    assert {"Linux", "macOS", "Git Bash"}.issubset(
        set(re.findall(r"Linux|macOS|Git Bash", section))
    )
    assert "bash" in languages


def test_ci_equivalent_section_pins_the_linux_lock_boundary() -> None:
    section = _section(_text(ROOT_README), "### CI-equivalent checks")
    image_match = re.search(r"(?m)^ARG PYTHON_IMAGE=(?P<image>\S+)$", _text(DOCKERFILE))
    assert image_match is not None, "Dockerfile must declare its pinned PYTHON_IMAGE"
    pinned_image = image_match.group("image")

    for token in (pinned_image, "backend/Dockerfile", "pip-tools==7.6.1", "container"):
        assert token in section


def test_troubleshooting_covers_database_health_and_migration_boundary() -> None:
    section = _section(_text(ROOT_README), "## Troubleshooting")

    for token in (
        "/health/live",
        "docker compose ps",
        "docker compose logs",
        "BACKEND_PORT",
        "POSTGRES_PORT",
        "P2-01",
    ):
        assert token in section


def test_dbml_and_finalized_contracts_share_an_authority_marker() -> None:
    paragraphs = re.split(r"\n\s*\n", _text(ROOT_README))
    authority_paragraphs = [
        paragraph
        for paragraph in paragraphs
        if "authoritative" in paragraph.lower()
        and not all(
            line.lstrip().startswith("- ") for line in paragraph.splitlines() if line.strip()
        )
    ]

    assert any(
        DBML_TARGET in paragraph and CONTRACTS_TARGET in paragraph
        for paragraph in authority_paragraphs
    )


def test_root_readme_links_the_canonical_project_layout() -> None:
    assert LAYOUT_TARGET in _link_targets(_text(ROOT_README))
