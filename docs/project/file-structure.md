# Business Management Platform — Project File Structure

**Status:** Canonical organization for Phase 1 onward  
**Established:** 2026-08-16  
**Repository name:** `business-management-platform`

## 1. Naming rules

- Use lowercase `kebab-case` for folders and documentation filenames.
- Root convention files retain their ecosystem-standard uppercase names: `README.md`, `CONTRIBUTING.md`, and `LICENSE`.
- Use lowercase `snake_case` for Python modules and packages.
- Use `PascalCase` for Python classes and `UPPER_SNAKE_CASE` for environment variables.
- Do not use spaces, parentheses, download suffixes such as `(1)`, or words such as `FINAL`, `VERIFIED`, `LATEST`, and `NEW` in active repository filenames.
- Retain a version in a filename only when it is part of a frozen artifact's identity, specifically Specification v1.2 and ERD v1.2. Contract and conventions revisions remain in document headers and Git history.
- Use Git history and tags for ordinary revisions. Do not create `file-final-final-2` copies.
- Keep exactly one active canonical copy of every artifact. Older drafts and downloaded duplicates belong outside the repository in the archive described in §5.
- The `.dbml` file is authoritative for the ERD. The PDF is a generated visual export.
- The accepted master specification's Decision Log is authoritative. Do not maintain a second editable Decision Log unless the project formally changes that rule.

## 2. Canonical repository hierarchy

```text
business-management-platform/
├── .gitattributes
├── .github/
│   ├── workflows/
│   │   └── ci.yml
│   └── pull_request_template.md
├── backend/
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── alembic/
│   │   ├── versions/
│   │   │   ├── 001_create_businesses_roles_users.py
│   │   │   ├── 002_create_customers_staff_services_availability.py
│   │   │   └── 003_create_bookings_payments_activity_refresh_tokens.py
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── bookings.py
│   │   │   │   │   ├── customers.py
│   │   │   │   │   ├── services.py
│   │   │   │   │   ├── staff.py
│   │   │   │   │   └── users.py
│   │   │   │   └── router.py
│   │   │   └── dependencies.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── errors.py
│   │   │   ├── logging.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── middleware/
│   │   │   ├── error_handler.py
│   │   │   └── request_id.py
│   │   ├── models/
│   │   │   ├── activity_log.py
│   │   │   ├── booking.py
│   │   │   ├── business.py
│   │   │   ├── customer.py
│   │   │   ├── payment.py
│   │   │   ├── refresh_token.py
│   │   │   ├── role.py
│   │   │   ├── service.py
│   │   │   ├── staff.py
│   │   │   ├── staff_availability.py
│   │   │   └── user.py
│   │   ├── repositories/
│   │   │   └── __init__.py
│   │   ├── schemas/
│   │   │   └── __init__.py
│   │   ├── services/
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   └── main.py
│   ├── tests/
│   │   ├── contract/
│   │   │   ├── test_auth_contract.py
│   │   │   ├── test_bookings_contract.py
│   │   │   ├── test_customers_contract.py
│   │   │   ├── test_services_contract.py
│   │   │   ├── test_staff_contract.py
│   │   │   └── test_users_contract.py
│   │   ├── integration/
│   │   │   └── test_tenant_isolation.py
│   │   ├── unit/
│   │   │   └── __init__.py
│   │   ├── conftest.py
│   │   └── factories.py
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── config/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── bookings/
│   │   │   ├── customers/
│   │   │   ├── dashboard/
│   │   │   ├── services/
│   │   │   ├── settings/
│   │   │   ├── staff/
│   │   │   └── users/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── types/
│   │   ├── utils/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── docs/
│   ├── project/
│   │   ├── master-specification-v1.2.docx
│   │   ├── implementation-backlog.md
│   │   ├── phase-0-artifacts.sha256
│   │   ├── requirements-sources.md
│   │   └── file-structure.md
│   ├── architecture/
│   │   ├── erd/
│   │   │   ├── source/
│   │   │   │   └── business-management-platform-erd-v1.2.dbml
│   │   │   └── exports/
│   │   │       └── business-management-platform-erd-v1.2.pdf
│   │   └── diagrams/
│   ├── api/
│   │   ├── shared-api-conventions.md
│   │   └── contracts/
│   │       ├── authentication-api-contract.md
│   │       ├── bookings-api-contract.md
│   │       ├── customers-api-contract.md
│   │       ├── services-api-contract.md
│   │       ├── staff-api-contract.md
│   │       └── users-api-contract.md
│   ├── deployment/
│   │   ├── local-development.md
│   │   ├── deployment-runbook.md
│   │   └── backup-and-recovery.md
│   └── testing/
│       ├── test-strategy.md
│       └── contract-traceability.md
├── scripts/
│   ├── seed_demo_data.py
│   └── verify_schema_parity.py
├── .editorconfig
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── compose.yaml
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

This is the target hierarchy, not a requirement to commit empty directories. Files and folders that belong to later backlog tasks are added only when their task begins. Python package directories contain `__init__.py`; intentionally reserved non-Python directories use a short `README.md` instead of indiscriminate `.gitkeep` files. The Phase 1 frontend may be a minimal containerized placeholder, while `users-api-contract.md` is created and accepted in P4U-01 before user endpoints are implemented.

`backend/pyproject.toml` is the single editable source of dependency and tool configuration. `backend/requirements.txt` exists only to satisfy the frozen §14 layout and container/deployment compatibility: it is a generated, pinned export from `pyproject.toml`, must carry a `DO NOT EDIT` header, and is regenerated and checked in CI whenever dependencies change. It is never hand-edited or maintained as an independent dependency list.

`frontend/src/features/dashboard/` owns dashboard-specific query and presentation logic. `frontend/src/pages/` contains routed page composition. A shared `frontend/src/test/` directory is intentionally omitted: Phase 6 will select the frontend test framework and then document either colocated `*.test.tsx` files or a centralized test directory, as delegated by Specification §21.3.

`alembic.ini` must define the revision filename convention, for example `file_template = %%(rev)s_%%(slug)s`, and migrations 001–003 must be created with explicit revision IDs rather than hand-renamed after generation.

## 3. Finalized Phase 0 file mapping

| Current finalized artifact | Canonical repository destination |
|---|---|
| `Business_Management_Platform_Specification_v1_2_PHASE0_COMPLETE_ACCEPTED.docx` | `docs/project/master-specification-v1.2.docx` |
| `Business_Management_Platform_IMPLEMENTATION_BACKLOG_ACCEPTED_PHASE0_EXIT.md` | `docs/project/implementation-backlog.md` |
| `api_conventions_FINAL_REVISION_3_COMPLETE_VERIFIED.md` | `docs/api/shared-api-conventions.md` |
| `auth_contract(1).md` | `docs/api/contracts/authentication-api-contract.md` |
| `Customers_API_Contract_FINAL_v2.md` | `docs/api/contracts/customers-api-contract.md` |
| `staff_contract_FINAL_REVISION_2.md` | `docs/api/contracts/staff-api-contract.md` |
| `services_contract.md` | `docs/api/contracts/services-api-contract.md` |
| `bookings_contract_FINAL_REVISION_2_VERIFIED.md` | `docs/api/contracts/bookings-api-contract.md` |
| `business_management_platform_erd_v1_2(1).dbml` | `docs/architecture/erd/source/business-management-platform-erd-v1.2.dbml` |
| `Business Management Platform — ERD v1.2 Final.pdf` | `docs/architecture/erd/exports/business-management-platform-erd-v1.2.pdf` |

The destination filenames intentionally omit words such as `FINAL`, `ACCEPTED`, and `VERIFIED`. Those are document status values, not filename identity. Git records later changes without producing numbered download copies.

## 4. Scoped artifact authority

Authority is scoped rather than expressed as one flat ranking:

- Accepted Decision Log entries resolve post-freeze decisions and override contradictory earlier specification text.
- `docs/api/shared-api-conventions.md` is authoritative for shared, cross-cutting API behavior.
- Each finalized contract in `docs/api/contracts/` is authoritative for that endpoint's fields, permissions, filters, transitions, and endpoint-specific behavior.
- `docs/architecture/erd/source/business-management-platform-erd-v1.2.dbml` is authoritative for schema details, constraints, indexes, checks, relationships, deletion rules, and schema notes.
- `docs/project/master-specification-v1.2.docx` remains authoritative for frozen product scope and requirements not delegated to another artifact.
- The ERD PDF is a viewing export only and never overrides the DBML.

Do not resolve a conflict by mechanically choosing the document listed first. Stop implementation, document the exception explicitly in the owning artifact, and add a Decision Log entry when the exception is material or changes frozen architecture or scope.

## 5. Archive hierarchy outside the Git repository

Keep obsolete drafts, original downloads, duplicate verification copies, and one-off document-editing scripts outside the repository:

```text
business-management-platform-archive/
├── incoming-originals/
├── phase-0-drafts/
│   ├── api-contracts/
│   ├── backlog/
│   ├── erd/
│   └── specification/
├── phase-0-authoring-scripts/
└── duplicate-downloads/
```

Move files with names such as `(1)`, `(2)`, `REVIEW_DRAFT`, `COMPLETE_VERIFIED`, `verified_downloads`, and obsolete Python document-editing scripts into this archive. Do not commit the archive to GitHub. Do not delete it until the canonical repository files have been copied, opened, and checksum-verified.

## 6. Immediate P1-01 setup order

1. Create the `business-management-platform/` repository root.
2. Create `backend/`, `frontend/`, `docs/`, `.github/`, and `scripts/`.
3. Compute `docs/project/phase-0-artifacts.sha256` from the ten accepted source artifacts using their intended canonical relative paths, before copying those artifacts into the repository.
4. Copy and rename the ten accepted Phase 0 artifacts using the mapping in §3.
5. Add `docs/project/requirements-sources.md` with the scoped authority rules in §4.
6. Copy this guide to `docs/project/file-structure.md` and add the root `.gitattributes` rules documented by the hierarchy.
7. Verify the repository copies against the precomputed manifest using `sha256sum -c docs/project/phase-0-artifacts.sha256`.
8. Confirm `backend/tests/integration/test_tenant_isolation.py` is part of the Phase 1 test scaffold.
9. Create the initial Git commit only after no active filename contains `(1)`, `(2)`, `FINAL`, `VERIFIED`, or `REVIEW_DRAFT`.
