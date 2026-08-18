# Business Management Platform

A contract-first, multi-tenant management platform for appointment-based and service businesses.

The project is being developed as a modular monolith using FastAPI, PostgreSQL, React, and TypeScript. Its first working profile will represent a salon, followed by a repair-shop reskin to demonstrate how one core platform can support different service-business terminology and workflows.

> **Current status:** Phase 0 is complete. Phase 1 repository and development-environment setup is beginning.

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

Every authenticated request loads the user's current business, role, and active status from PostgreSQL. Authorization does not rely on stale role or tenant claims embedded in access tokens.

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

Implementation proceeds in strict backlog order. The current task is **P1-03: implement typed environment configuration**. Progress against the backlog is tracked in `docs/project/progress.md`.

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

The backend scaffold exists as of P1-02: `cd backend && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"`, then `.venv/Scripts/uvicorn app.main:app --reload` (Windows; use `.venv/bin/` on Linux/macOS). See `backend/README.md`.
Docker commands, migrations, database-backed tests, linting, and type-checking commands are added during the rest of Phase 1 and documented in full under backlog task P1-08.

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

This project is licensed under the [MIT License](LICENSE).
