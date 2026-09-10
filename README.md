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

## Local development

Docker Compose runs the backend and PostgreSQL. Copy `.env.example` to `.env`, replace the deliberately
invalid `JWT_SECRET` sentinel, then run `docker compose up --build --wait` from the repository root.
See [local development with Docker Compose](docs/deployment/local-development.md) for prerequisites,
health checks, logs, database access, persistence verification, and safe reset instructions.

Native backend development remains available through `backend/README.md`. On Windows, install from
the editable `backend/pyproject.toml` source; `backend/requirements.txt` is the generated Linux-container
and deployment lock and is not a Windows installation input. The database-backed test harness is
planned for P1-06 and CI for P1-07. Migration configuration begins in P2-01; its explicit release-step
mechanism remains deferred to DEP-01.

## Quality checks

After installing the backend development dependencies, activate the backend virtual environment.
From the repository root:

```bash
python scripts/quality.py format
python scripts/quality.py lint
python scripts/quality.py typecheck
python -m pytest -c backend/pyproject.toml backend/tests
python -m pytest tests/hooks
```

`format` applies Ruff fixes; `lint` checks formatting and lint without changing files. Type checking
uses strict mypy. The two pytest commands collect the backend and repository-tooling suites
separately. Frontend executable checks begin in P6-01.

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
