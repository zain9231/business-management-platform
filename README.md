# Business Management Platform

A contract-first, multi-tenant management platform for appointment-based and service businesses.

The project is being developed as a modular monolith using FastAPI, PostgreSQL, React, and TypeScript. Its first working profile will represent a salon, followed by a repair-shop reskin to demonstrate how one core platform can support different service-business terminology and workflows.

> **Current status:** Phase 0 is complete. The backend scaffold, typed configuration, Docker environment, and Python quality tooling are implemented. See [implementation progress](docs/project/progress.md) for current task status.

## Problem and scope

Small service businesses often manage customers, staff schedules, services, and bookings across disconnected spreadsheets, calendars, and messaging applications. This project brings those workflows into one tenant-isolated system with explicit permissions and auditable business operations.

The MVP is intended for service businesses such as salons, cleaning companies, and repair shops. It is not designed for hotels, vehicle rentals, healthcare records, or other domains requiring fundamentally different inventory, occupancy, or regulatory models.

## Planned MVP

- JWT authentication with refresh-token rotation
- Tenant isolation across all business-owned data
- Administrator, Manager, and Staff permissions
- Customer management
- Staff management and weekly availability
- Service management
- Booking creation, rescheduling, conflict detection, and status transitions
- Business-local timezone and DST-aware availability evaluation
- Dashboard summary and recent activity
- Audit logging for important business operations
- Configuration-driven terminology and custom fields in later phases

These features are planned and contractually specified but are not all implemented yet.

## Architecture and technology

| Area | Planned technology |
|---|---|
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Database | PostgreSQL |
| Frontend | React, TypeScript, Vite, Tailwind CSS, TanStack Query |
| Local environment | Docker and Docker Compose |
| Testing | Pytest for backend unit, integration, contract, and tenant-isolation tests; Vitest and Testing Library for frontend tests; Playwright for end-to-end tests |
| CI | GitHub Actions |
| Architecture | Multi-tenant modular monolith |

The authentication design requires every protected request to load the user's current business,
role, and active status from PostgreSQL. Its implementation belongs to Phase 3.

## Project status

Phase 0 produced the frozen planning and contract artifacts required before implementation:

- Master specification and accepted Decision Log
- Authoritative DBML ERD and PDF export
- Shared API conventions
- Authentication contract
- Customers contract
- Staff and availability contract
- Services contract
- Bookings contract
- Accepted implementation backlog

Implementation proceeds in strict backlog order. Current task status is tracked in
`docs/project/progress.md`.

## Project documentation

- [Master specification](docs/project/master-specification-v1.2.docx)
- [Implementation backlog](docs/project/implementation-backlog.md)
- [Requirements and authority rules](docs/project/requirements-sources.md)
- [Canonical repository structure](docs/project/file-structure.md)
- [Shared API conventions](docs/api/shared-api-conventions.md)
- [API contracts](docs/api/contracts/)
- [Authoritative DBML ERD](docs/architecture/erd/source/business-management-platform-erd-v1.2.dbml)
- [ERD PDF](docs/architecture/erd/exports/business-management-platform-erd-v1.2.pdf)

The [DBML source](docs/architecture/erd/source/business-management-platform-erd-v1.2.dbml) is the
authoritative data model, and the finalized documents under [API contracts](docs/api/contracts/) are
the authoritative endpoint and behavior contracts.

## Local development

Developer prerequisites are Git, Python 3.13, Docker Desktop or Docker Engine using Linux
containers, and Docker Compose. Git Bash is also required on Windows for the CI-equivalent Bash
sequence below.

Docker Compose runs the backend and PostgreSQL. Copy `.env.example` to `.env`, replace the deliberately
invalid `JWT_SECRET` sentinel, then run the following from the repository root on Linux, macOS, or
Git Bash. The defaults remain 5432 and 8000; proof runs override them with run-owned ports.

```bash
POSTGRES_PORT="${POSTGRES_PORT:-5432}" BACKEND_PORT="${BACKEND_PORT:-8000}" \
  docker compose up --build --wait
```

See [local development with Docker Compose](docs/deployment/local-development.md) for prerequisites,
health checks, logs, database access, persistence verification, and safe reset instructions.

Native backend development remains available through `backend/README.md`. On Windows, install from
the editable `backend/pyproject.toml` source; `backend/requirements.txt` is the generated Linux-container
and deployment lock and is not a Windows installation input. The database-backed test harness is
available now; see `backend/README.md` for its guarded PostgreSQL setup, unit/fast/full modes, and
coverage command. GitHub Actions now runs the pinned, hash-checked CI gate. Migration configuration
begins in P2-01; until then, CI rejects any partial Alembic surface. Its explicit release-step
mechanism remains deferred to DEP-01.

## Quality checks

After installing the backend development dependencies, activate the backend virtual environment.
From the repository root:

```bash
python scripts/quality.py format
python scripts/quality.py lint
python scripts/quality.py typecheck
TEST_DATABASE_URL="${TEST_DATABASE_URL:?set an explicit URL for the owned test database}" \
  python -m pytest -c backend/pyproject.toml backend/tests
python -m pytest tests/hooks
```

`format` applies Ruff fixes; `lint` checks formatting and lint without changing files. Type checking
uses strict mypy. The backend command is the full gate and requires PostgreSQL; its documented fast
loop also includes integration and deployment tests. `python -m pytest -c backend/pyproject.toml
backend/tests -m unit` is the database-free loop when run with
`TEST_DATABASE_URL=not-a-database-url`. Repository-tooling tests remain separate. Frontend executable
checks begin in P6-01.

### CI-equivalent checks

This sequence is Bash for Linux, macOS, or Git Bash and runs from the repository root of a pristine
checkout. Unlike the ordinary [backend setup](backend/README.md#setup), it uses a Python environment
outside the checkout. On Windows, build that environment from a Git-archived copy of
`backend/pyproject.toml`; do not install the Linux-only development lock with Windows Python. Set
`PYTHONPATH` to the pristine checkout's `backend` directory and verify imports resolve there.

Keep all writable state outside the checkout: the Python environment and build metadata, pip cache,
`RUNNER_TEMP` (including the lock reproduction tree, Gitleaks files, command captures, and all pytest
basetemps), `PRE_COMMIT_HOME`, and the run-owned PostgreSQL service and data. The PostgreSQL service
must be verified as belonging to this run before setting `POSTGRES_PORT` and `TEST_DATABASE_URL`.
The commands below orchestrate on the host except for the two `pip-compile` lines. That
container-executed lock step uses pinned `pip-tools==7.6.1` in the Linux/AMD64 image read from
`backend/Dockerfile`. The two `cmp` commands then run back on the host.

```bash
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PYTHONDONTWRITEBYTECODE=1
: "${RUNNER_TEMP:?set RUNNER_TEMP outside the checkout}"
: "${PIP_CACHE_DIR:?set PIP_CACHE_DIR outside the checkout}"
: "${PRE_COMMIT_HOME:?set PRE_COMMIT_HOME outside the checkout}"
export PYTHONPATH="$PWD/backend"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export POSTGRES_PORT
TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgresql+psycopg://postgres:postgres@127.0.0.1:${POSTGRES_PORT}/bmp_test}"
export TEST_DATABASE_URL

python -c 'import pathlib, app; expected=(pathlib.Path.cwd()/"backend"/"app").resolve(); actual=pathlib.Path(app.__file__).resolve(); print(actual); assert actual.is_relative_to(expected)'
python -m pip check
lock_repro_root="$RUNNER_TEMP/lock-repro"
mkdir -p "$lock_repro_root"
git archive HEAD backend | tar -x -C "$lock_repro_root"
expected_python_image="python:3.13.15-slim-bookworm@sha256:0f16c5d35fe6464ee471792ab3bb9116f911b65b3fbf10120c98d2bdc6332f48"
python_image="$(sed -n 's/^ARG PYTHON_IMAGE=//p' backend/Dockerfile)"
test "$python_image" = "$expected_python_image"
lock_backend="$lock_repro_root/backend"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) lock_backend_mount="$(cygpath -w "$lock_backend")" ;;
  *) lock_backend_mount="$lock_backend" ;;
esac
MSYS_NO_PATHCONV=1 docker run --rm --platform linux/amd64 \
  --mount "type=bind,source=$lock_backend_mount,target=/work" \
  --workdir /work \
  --env PIP_DISABLE_PIP_VERSION_CHECK=1 \
  "$python_image" sh -euc '
    python -m pip install --require-hashes --requirement requirements-dev.txt
    test "$(python -c '\''from importlib.metadata import version; print(version("pip-tools"))'\'')" = "7.6.1"
    pip-compile --allow-unsafe --generate-hashes --output-file=requirements.txt pyproject.toml
    pip-compile --allow-unsafe --extra dev --generate-hashes \
      --output-file=requirements-dev.txt pyproject.toml
  '
cmp --silent backend/requirements.txt "$lock_repro_root/backend/requirements.txt"
cmp --silent backend/requirements-dev.txt "$lock_repro_root/backend/requirements-dev.txt"
python -m pip check
python scripts/quality.py lint
python scripts/quality.py typecheck
python scripts/validate_migrations.py
TEST_DATABASE_URL=not-a-database-url python -m pytest -c backend/pyproject.toml \
  backend/tests -m unit -p no:cacheprovider --basetemp="$RUNNER_TEMP/pytest-unit"
TEST_DATABASE_URL="$TEST_DATABASE_URL" \
  python -m pytest -c backend/pyproject.toml backend/tests -p no:cacheprovider \
  --basetemp="$RUNNER_TEMP/pytest-full"
python -m pytest tests/hooks -p no:cacheprovider --basetemp="$RUNNER_TEMP/pytest-tooling"
SKIP=gitleaks,gitleaks-dir python -m pre_commit run --all-files --show-diff-on-failure
git diff --exit-code
checkout_status="$(git status --porcelain=v1 --untracked-files=all --ignored)"
test -z "$checkout_status"
gitleaks dir --redact --no-banner --verbose .
sha256sum -c docs/project/phase-0-artifacts.sha256
```

Unit mode is database-free. The full suite requires PostgreSQL. The Gitleaks `dir` command scans the
checked-out files, including `.git` metadata, but it is not a full-history scan.

Install the Git hooks once in every clone, from the repository root with that environment active:

```bash
python -m pre_commit install --install-hooks
python -m pre_commit run --all-files
```

The first command downloads the pinned hook environments and installs `.git/hooks/pre-commit`.
The configuration file alone does not activate commit checks. Hooks can modify unprotected files;
review their changes before staging. Gitleaks scans the staged changes at commit time. The separate
manual `gitleaks-dir` hook scans the working directory; `--all-files` does not turn the staged scanner
into a working-directory or history scan.

## Troubleshooting

If Compose does not become healthy, confirm the run-owned `BACKEND_PORT` and `POSTGRES_PORT`, then
check `docker compose ps`. Request `/health/live` on the selected backend port and inspect
`docker compose logs backend` and `docker compose logs db` before rebuilding or resetting anything.
Alembic migration configuration begins in P2-01, so missing migration commands before that task are
expected rather than a database-health remedy.

## Phase 0 artifact verification

The checksum manifest covers the ten accepted Phase 0 source artifacts. It intentionally excludes itself and supporting repository guides such as this README.

On Linux, macOS, or Git Bash, run this command from the repository root:

```bash
sha256sum -c docs/project/phase-0-artifacts.sha256
```

On Windows PowerShell, run:

```powershell
$failed = 0
Get-Content ".\docs\project\phase-0-artifacts.sha256" | ForEach-Object {
    $expected, $file = $_ -split '\s+', 2
    $file = $file.Trim()
    if (-not (Test-Path $file)) {
        Write-Host "MISSING  $file" -ForegroundColor Red
        $failed++
    } else {
        $actual = (Get-FileHash -Algorithm SHA256 $file).Hash.ToLower()
        if ($actual -eq $expected) {
            Write-Host "OK       $file" -ForegroundColor Green
        } else {
            Write-Host "FAIL     $file" -ForegroundColor Red
            $failed++
        }
    }
}
Write-Host "`nFailures: $failed"
```

The manifest's own SHA-256 is:

```text
a84e2b1f490bb9ac3e94c806faeb2a5a051a67b6b27a8e5c8410412a942cf5f8
```

Record that value in the annotated `phase-0-complete` Git tag message so the manifest itself is tamper-evident.

Do not add old downloads, review drafts, numbered copies such as `(1)` or `(2)`, or files named `FINAL`, `VERIFIED`, `LATEST`, or `NEW` to the repository.

## License

Copyright (c) 2026 Zain-ul-Abideen. All rights reserved. See [LICENSE](LICENSE).

This repository is source-available for review, not open source. It is published so the engineering
process — specification, API contracts, tests, and commit history — can be read by prospective
employers and collaborators. No licence to use, copy, modify, or distribute the software is granted.
Commits up to and including `b1c9f78` were published under the MIT License and remain
licensed under it for those versions only.
