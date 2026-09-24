"""Contract tests for the P1-08 developer documentation."""

from __future__ import annotations

import re
import subprocess
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


def test_local_development_dump_outputs_are_ignored() -> None:
    documentation = _text(LOCAL_DEVELOPMENT)
    dump_blocks = [
        (language.lower(), body)
        for language, body in _fenced_blocks(documentation)
        if "pg_dump" in body
    ]
    assert dump_blocks, "local-development.md must document at least one dump command"
    assert documentation.count("pg_dump") == len(dump_blocks), (
        "each documented pg_dump command must have one fenced block"
    )
    assert {language for language, _ in dump_blocks} == {"powershell", "bash"}

    for language, body in dump_blocks:
        assert body.count("pg_dump") == 1, "each dump block must have one pg_dump"
        pattern = (
            r"(?m)\bSet-Content\s+-Encoding\s+utf8\s+(?P<path>\S+)"
            if language == "powershell"
            else r"(?m)^\s*>\s*(?P<path>\S+)\s*$"
        )
        output_match = re.search(pattern, body)
        assert output_match is not None, f"{language} dump output is not identified"
        output = output_match.group("path").strip("'\"")
        assert output and not Path(output).is_absolute()

        result = subprocess.run(
            [
                "git",
                "-C",
                str(REPOSITORY_ROOT),
                "check-ignore",
                "-v",
                "--no-index",
                "--",
                output,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"{output} is not ignored by the repository .gitignore: {result.stderr}"
        )
        source = result.stdout.partition("\t")[0].split(":", maxsplit=1)[0]
        assert source == ".gitignore", (
            f"{output} must be ignored by the repository .gitignore, not {source}"
        )


def test_ci_equivalent_environment_setup_precedes_import_check() -> None:
    section = _section(_text(ROOT_README), "### CI-equivalent checks")
    bash_blocks = [body for language, body in _fenced_blocks(section) if language == "bash"]
    import_index = next(
        (index for index, body in enumerate(bash_blocks) if "import pathlib, app" in body),
        None,
    )
    assert import_index is not None, "CI-equivalent import-origin check is missing"
    assert import_index > 0, "external environment setup must precede the import check"
    setup = bash_blocks[import_index - 1]
    for token in (
        "${RUNNER_TEMP:?",
        "git archive HEAD backend",
        'python -m venv "$RUNNER_TEMP/',
        "Scripts/activate",
        "bin/activate",
        'pip install -e ".[dev]"',
    ):
        assert token in setup, f"external environment setup lacks {token}"
    assert "requirements-dev.txt" not in setup
