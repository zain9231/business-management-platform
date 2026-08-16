# Business Management Platform — Implementation Backlog

**Status:** ACCEPTED — Phase 0 exit artifact  
**Prepared:** 2026-08-16  
**Scope:** Converts Master Specification §55.1 into implementation-sized work in the strict Phase 1–13 build order. Phase 14 remains a separate future project.

**Review Draft 2 corrections:** JWTs retain identity-only claims; Administrator user management is a contract-first Phase 4C slice; business onboarding is explicitly seed/operations-only; the full frozen dashboard scope is retained; tenant-owned role seeding, booking audit wording, and the backend package layout are corrected.

## 1. Authority and execution rules

Implement against these sources, in this order of authority:

1. Accepted Master Specification Decision Log entries.
2. Shared API Conventions — FINAL, Revision 3.
3. The finalized Auth, Customers, Staff, Services, and Bookings API contracts.
4. The authoritative DBML ERD for schema details.
5. The remaining frozen Master Specification text.

Rules for using this backlog:

- Work phases in order. Within a phase, follow explicit dependencies.
- One checklist item is one GitHub issue and should fit one or two focused sittings.
- A task is not complete until its implementation, required automated tests, and affected documentation are committed together.
- Never implement from the ERD PDF when the DBML contains more precise constraints, indexes, notes, or relationship rules.
- Every tenant-owned query, count, relationship check, lock, and mutation must be tenant-scoped in the database operation itself.
- Do not build Phase 8 configuration/custom-field behavior before the hard-coded customer–staff–service–booking vertical slice works.
- Perform the first deployment immediately after Auth and Customers pass their contract gates. Do not wait for Staff, Services, Bookings, or a polished frontend.
- Billing/payments remain Phase 9 stretch work and require their own contract before implementation.
- Administrator-only user management is included as a contract-first Phase 4C slice; no user endpoints may be implemented until that contract and its test list are accepted.
- The MVP has no public/self-service business registration. Demo/operations provisioning creates each business, its three tenant-owned role rows, and its initial Administrator; any onboarding API requires a future contract and accepted scope change.
- Phase 14 public booking/marketing work is outside this repository and outside the MVP.

## 2. Task-level definition of done

Every checked task must satisfy all applicable items:

- [ ] Code is formatted, linted, type-checked, and reviewed against its authoritative artifact.
- [ ] Success, failure, authorization, tenant-isolation, and transaction behavior are tested where applicable.
- [ ] Tests fail before the implementation and pass afterward.
- [ ] No secrets, tokens, tenant data, stack traces, or database details leak through logs or responses.
- [ ] Database changes include upgrade, clean-database replay, and downgrade/rollback verification where safe.
- [ ] API changes retain the shared error envelope, strict-input behavior, and deterministic response rules.
- [ ] The README, `.env.example`, runbook, or Decision Log is updated when the task changes setup, behavior, limitations, or architecture.
- [ ] The branch is mergeable without relying on uncommitted local state.

## 3. Milestones and hard gates

| Milestone | Required outcome | Gate to continue |
|---|---|---|
| Phase 1 | Reproducible repository and local environment | CI and local test harness pass |
| Phase 2 | Schema and shared backend foundation | Fresh migration replay and tenant-isolation foundation pass |
| Phase 3 | Authentication and authorization | All Auth Contract tests 1–18 pass |
| Phase 4A | Customers vertical slice | All Customers Contract tests 1–15 pass |
| First deployment | Auth + Customers available remotely | Deployment smoke tests pass |
| Phase 4B | Staff, availability, and Services | Staff tests 1–18 and Services tests 1–18 pass |
| Phase 4C | Administrator user management | Users Contract and its complete test list pass |
| Phase 5 | Booking engine | Bookings tests 1–23 pass, including concurrency/DST suites |
| Phases 6–7 | Usable frontend and end-to-end core workflow | Core salon workflow passes browser-level tests |
| Phase 8 | Configuration and repair-shop reskin | Same codebase demonstrates both profiles |
| Phases 10–12 | Hardened production demo | Security, regression, recovery, and deployment gates pass |
| Phase 13 | Portfolio-ready release | Documentation and demo checklist pass |

---

## Phase 1 — Repository and development environment

### P1-01 — Initialize repository structure and branch policy (1 sitting)

- [ ] Create the modular-monolith root layout: `backend/`, `frontend/`, `docs/`, and deployment/configuration files.
- [ ] Add `.gitignore`, `.gitattributes` (LF text normalization and binary PDF/DOCX rules), `.editorconfig`, license choice, contribution notes, and the agreed branch/commit convention.
- [ ] Protect `main` conceptually through the documented pull-request workflow, even if working solo.
- [ ] Compute `docs/project/phase-0-artifacts.sha256` from the ten accepted source artifacts using their intended canonical relative paths, before copying them into the repository.
- [ ] Copy the ten accepted Phase 0 artifacts into their canonical repository paths and stable filenames.
- [ ] Record the scoped artifact authority and canonical filenames in `docs/project/requirements-sources.md`.
- [ ] Verify the repository copies against the precomputed `docs/project/phase-0-artifacts.sha256` manifest before the first commit.
- **Depends on:** Phase 0 artifacts only.

### P1-02 — Scaffold the FastAPI backend package (1 sitting)

- [ ] Create `main.py` and the application package boundaries: `api/`, `models/`, `schemas/`, `services/`, `repositories/`, `middleware/`, `core/`, `db/`, and `tests/`.
- [ ] Add pinned runtime and development dependencies for FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, JWT, Argon2id, and testing.
- [ ] Add a minimal application factory and `/health/live` placeholder without domain behavior.
- [ ] Confirm the backend starts from one documented command.
- **Depends on:** P1-01.

### P1-03 — Implement typed environment configuration (1 sitting)

- [ ] Add settings for database URL, JWT secret, issuer, audience, access/refresh lifetimes, CORS origins, environment, and logging level.
- [ ] Fail fast on missing or unsafe production values.
- [ ] Create `.env.example` containing safe placeholders only.
- [ ] Test development/test configuration loading and production validation.
- **Depends on:** P1-02.

### P1-04 — Add Docker Compose with PostgreSQL (1 sitting)

- [ ] Add a pinned PostgreSQL service, named development volume, health check, and backend service wiring.
- [ ] Keep production credentials out of Compose and source them from environment variables.
- [ ] Document start, stop, logs, database shell, and recoverable volume-reset commands.
- [ ] Verify a clean clone reaches a healthy database and backend.
- **Depends on:** P1-02, P1-03.

### P1-05 — Configure formatting, linting, and type checking (1 sitting)

- [ ] Configure Ruff formatting/linting and strict-enough Python type checking.
- [ ] Configure frontend lint/format placeholders without building the Phase 6 UI.
- [ ] Add pre-commit hooks for whitespace, formatting, linting, and accidental-secret checks.
- [ ] Add single-command `format`, `lint`, and `typecheck` developer workflows.
- **Depends on:** P1-01, P1-02.

### P1-06 — Establish the automated test harness (1–2 sittings)

- [ ] Configure pytest, async/sync client choice, isolated test settings, deterministic time helpers, and coverage output.
- [ ] Provide test database creation, transaction cleanup, and factories for two businesses and all three roles.
- [ ] Add markers for unit, integration, concurrency, DST, and deployment tests.
- [ ] Prove isolation with two tests that cannot observe each other's committed data.
- **Depends on:** P1-03, P1-04.

### P1-07 — Add continuous integration (1 sitting)

- [ ] Run formatting check, lint, type checking, migration validation, unit tests, and integration tests against PostgreSQL.
- [ ] Cache dependencies without caching generated application state.
- [ ] Fail on migration drift, test failure, or leaked committed secrets.
- [ ] Display concise CI commands in the README.
- **Depends on:** P1-05, P1-06.

### P1-08 — Write the initial developer README (1 sitting)

- [ ] Document prerequisites, environment setup, Docker startup, test commands, lint/type-check commands, and project layout.
- [ ] State that DBML and finalized contracts are authoritative.
- [ ] Add a short troubleshooting section for database health and migrations.
- [ ] Confirm every command works from a clean checkout.
- **Depends on:** P1-04 through P1-07.

**Phase 1 exit gate:** A clean clone starts locally and passes the empty-project CI pipeline.

---

## Phase 2 — Database and shared backend foundation

### P2-01 — Configure SQLAlchemy sessions and Alembic (1 sitting)

- [ ] Add engine/session lifecycle with explicit transaction boundaries and safe connection cleanup.
- [ ] Configure Alembic to use application settings without embedding credentials.
- [ ] Create the migration test commands for upgrade, downgrade, and clean replay.
- [ ] Add a database readiness check distinct from liveness.
- **Depends on:** Phase 1 gate.

### P2-02 — Migration 001: businesses, roles, and users (1–2 sittings)

- [ ] Implement UUID primary keys, timestamps, active flags, global lowercase-email uniqueness, public-slug uniqueness, and fixed-role constraints exactly as DBML specifies.
- [ ] Add the defined indexes and foreign-key delete rules.
- [ ] Enforce the three fixed role names with the database check constraint; do not insert global role rows because every role row requires a tenant `business_id`.
- [ ] Test constraint violations and a clean upgrade/downgrade cycle.
- **Depends on:** P2-01.

### P2-03 — Migration 002: customers, staff, services, and availability (1–2 sittings)

- [ ] Create all columns, defaults, JSONB fields, checks, indexes, composite tenant keys, and restrictive foreign keys from the DBML.
- [ ] Preserve non-unique customer/staff emails and non-unique service names.
- [ ] Enforce service duration/price and availability weekday/window checks.
- [ ] Preserve `24:00:00` as a legal availability `end_time` value through an appropriate PostgreSQL-compatible representation.
- **Depends on:** P2-02.

### P2-04 — Migration 003: bookings, payments, activity logs, and refresh tokens (1–2 sittings)

- [ ] Create booking/payment enums and all tables, checks, indexes, composite foreign keys, and deletion rules from the DBML.
- [ ] Keep payments present but unused until the Phase 9 stretch gate.
- [ ] Implement refresh-token hash/expiry/revocation storage and append-oriented activity logs.
- [ ] Confirm bookings have no database/application hard-delete workflow.
- **Depends on:** P2-03.

### P2-05 — Verify DBML-to-migration parity (1–2 sittings)

- [ ] Build schema-introspection tests covering every table, enum, column, default, nullability rule, check, unique constraint, foreign key, delete rule, and required index.
- [ ] Explicitly test all tenant composite relationships and the bookings/payments composite relationship.
- [ ] Verify `staff_availability.end_time` stores and round-trips `24:00:00` without same-weekday normalization.
- [ ] Record any unavoidable ORM representation exception without changing the DBML's meaning.
- **Depends on:** P2-02 through P2-04.

### P2-06 — Implement ORM models and boundary types (1–2 sittings)

- [ ] Map every MVP DBML table without inventing schema fields.
- [ ] Add safe UUID, UTC timestamp, fixed-scale money, enum, JSONB, and availability wall-time handling.
- [ ] Ensure booking `end_time` is stored but never accepted as a client-controlled value.
- [ ] Add model-level round-trip tests, including `24:00:00`, decimals, nullable fields, and enums.
- **Depends on:** P2-05.

### P2-07 — Add transaction and repository primitives (1 sitting)

- [ ] Define the unit-of-work/transaction pattern used by mutations and audit inserts.
- [ ] Prevent repositories from committing independently inside a multi-row business operation.
- [ ] Add guarded update/`RETURNING` helpers for idempotent deactivation.
- [ ] Add rollback tests proving no partial domain/audit writes.
- **Depends on:** P2-06.

### P2-08 — Centralize tenant-scoped data access (1–2 sittings)

- [ ] Implement authenticated-tenant query helpers for reads, writes, counts, relationship references, and locks.
- [ ] Implement indistinguishable nonexistent/cross-tenant `404 not_found` lookup behavior, including request-body references.
- [ ] Prohibit client-supplied `business_id` from establishing authorization context.
- [ ] Add deliberate cross-tenant negative tests for each helper category.
- **Depends on:** P2-07.

### P2-09 — Implement shared API error handling and strict validation (1–2 sittings)

- [ ] Add the shared error envelope and full Revision 3 registry, including `inactive_resource`.
- [ ] Remap framework validation, HTTP, authentication, and unexpected exceptions; never expose `{"detail": ...}` in production responses.
- [ ] Reject unknown body fields/query parameters, malformed UUIDs, unsupported content types, and disallowed repeated parameters consistently.
- [ ] Add safe generic `500 internal_error` handling with protected diagnostic logging.
- **Depends on:** P1-02, P2-08.
- **Shared coverage:** Conventions §§3–5 and §12.

### P2-10 — Implement pagination, filtering, sorting, and literal-search utilities (1–2 sittings)

- [ ] Implement the shared pagination envelope and page bounds.
- [ ] Implement whitelisted single-field sorting with deterministic `id ASC` tie-breaking.
- [ ] Implement half-open range helpers and endpoint-specific filter composition.
- [ ] Escape `%`, `_`, and the configured SQL `LIKE` escape character in literal case-insensitive search.
- [ ] Test empty/out-of-range pages, stable duplicate ordering, malformed parameters, and injection-like search input.
- **Depends on:** P2-08, P2-09.
- **Shared coverage:** Conventions §§6–8 and §12.

### P2-11 — Implement activity-log service and audit vocabulary guard (1 sitting)

- [ ] Add an append-only activity writer that always receives authenticated business/user context.
- [ ] Define centrally validated entity/action strings used by finalized contracts.
- [ ] Require domain mutation and required activity record to share one transaction.
- [ ] Test audit insertion failure rollback and ensure secrets/tokens never enter activity descriptions.
- **Depends on:** P2-07, P2-09.
- **Shared coverage:** Conventions §9 and contract audit sections.

### P2-12 — Create deterministic multi-tenant seed data (1–2 sittings)

- [ ] Seed a Demo Salon and an isolated second business; create the three tenant-owned role rows per business, then Administrator/Manager/Staff users, linked staff rows, customers, services, and availability.
- [ ] Hash passwords with the real configured password hasher; never commit plaintext production credentials.
- [ ] Make seeding idempotent and explicitly development/demo-only.
- [ ] Add a reset-and-reseed verification test.
- **Depends on:** P2-02 through P2-11.

### P2-13 — Backend-foundation acceptance gate (1 sitting)

- [ ] Run migrations from empty PostgreSQL to head twice: once locally and once in CI.
- [ ] Run schema-parity, model round-trip, strict-error, pagination/search, audit rollback, and tenant-helper suites.
- [ ] Confirm no domain endpoint beyond health/readiness exists yet.
- [ ] Tag or record the Phase 2 checkpoint.
- **Depends on:** P2-01 through P2-12.

**Phase 2 exit gate:** The authoritative schema can be recreated exactly, and the shared tenant/error/transaction foundation passes.

---

## Phase 3 — Authentication and authorization

### P3-01 — Implement password hashing and JWT primitives (1–2 sittings)

- [ ] Configure Argon2id with the contract parameters, rehash-on-login, a fixed dummy hash, and a 1,024 UTF-8-byte input limit.
- [ ] Implement pinned-algorithm access/refresh JWT issuance and verification with required `iss`, `aud`, `sub`, `type`, `jti`, `iat`, and `exp`; embed no role, email, or business claim because those values are loaded from the database on every protected request.
- [ ] Reject `none`/unsupported algorithms, type confusion, missing/malformed claims, and incorrect issuer/audience uniformly.
- [ ] Unit-test cryptographic primitives without logging passwords or tokens.
- **Depends on:** Phase 2 gate.
- **Contract coverage:** Auth tests 13 and 17; primitives used by tests 1–10.

### P3-02 — Implement refresh-token persistence repository (1 sitting)

- [ ] Store only SHA-256 token hashes with user id, expiry, creation time, and nullable revocation time.
- [ ] Add tenant-independent self-scoped lookup/locking appropriate to authentication flows.
- [ ] Provide atomic rotate and revoke operations that cannot consume one token twice.
- [ ] Test raw-token absence from the database, logs, errors, and activity records.
- **Depends on:** P3-01, P2-07.
- **Contract coverage:** Auth tests 1, 3–5, 8–10, and 15.

### P3-03 — Implement `POST /auth/login` with audit (1–2 sittings)

- [ ] Normalize email, enforce password byte limit before hashing, and execute the dummy-hash path for unknown email.
- [ ] Return byte-identical credential failures for wrong password, unknown email, inactive user, and inactive business.
- [ ] On success, update `last_login`, persist refresh hash, write login activity, return claims/expiry, and add no-cache headers atomically.
- [ ] Implement rehash-on-login when stored parameters are outdated.
- **Depends on:** P3-01, P3-02, P2-11.
- **Contract coverage:** Auth tests 1, 2, 12, 16, and 17.

### P3-04 — Implement `POST /auth/refresh` with rotation (1–2 sittings)

- [ ] Validate refresh type/claims/signature and current user/business activity.
- [ ] Lock and rotate a valid refresh token in one transaction; revoke the old row and create the new row.
- [ ] Return uniform `401 invalid_token` for reused, expired, forged, wrong-type, or deactivated-principal refreshes.
- [ ] Add no-cache response headers.
- **Depends on:** P3-02, P3-03.
- **Contract coverage:** Auth tests 3, 4, 5, and 16.

### P3-05 — Implement protected-request dependency and `GET /auth/me` (1–2 sittings)

- [ ] Parse Bearer access tokens and distinguish missing, invalid, expired, nonexistent-principal, and inactive-account behavior exactly as contracted.
- [ ] Resolve role and business from the user's own `business_id`; accept no client tenant identifier.
- [ ] Return the correct Administrator/Manager/Staff representation without `password_hash`.
- [ ] Include `WWW-Authenticate: Bearer` on applicable 401 responses.
- **Depends on:** P3-01, P2-08.
- **Contract coverage:** Auth tests 6 and 7.

### P3-06 — Implement `POST /auth/logout` (1–2 sittings)

- [ ] Permit logout for a deactivated user when the supplied refresh token is otherwise valid.
- [ ] Lock and revoke the refresh row and write exactly one logout activity atomically.
- [ ] Return `204` on success and uniform `401 invalid_token` on replay.
- [ ] Assert that the access token remains valid until `exp`, as intentionally documented.
- **Depends on:** P3-02, P3-05, P2-11.
- **Contract coverage:** Auth tests 8, 9, and 10.

### P3-07 — Complete strict-input and token-adversary coverage (1 sitting)

- [ ] Test unknown body fields and query parameters across all four endpoints.
- [ ] Test garbage tokens, forged signatures, claim mutations, malformed UUID claims, wrong issuer/audience, wrong token type, and unsupported algorithms.
- [ ] Verify stable error codes, safe messages, exact 401 headers, and absence of sensitive data.
- **Depends on:** P3-03 through P3-06, P2-09.
- **Contract coverage:** Auth tests 4, 7, 11, 13, and 14.

### P3-08 — Complete auth concurrency and rollback tests (1–2 sittings)

- [ ] Race two refreshes of one token and prove exactly one succeeds.
- [ ] Race two logouts and prove one `204`, one uniform `401`, and exactly one audit record.
- [ ] Inject login-audit failure and prove `last_login`/refresh insertion roll back.
- [ ] Inject logout-audit failure and prove revocation rolls back.
- **Depends on:** P3-03, P3-04, P3-06.
- **Contract coverage:** Auth tests 5, 15, and 18.

### P3-09 — Authentication contract gate and limitation documentation (1 sitting)

- [ ] Run all Auth Contract tests 1–18 against PostgreSQL.
- [ ] Add README limitations: refresh token in `sessionStorage` in the future React client, XSS exposure, no access-token revocation, HTTPS requirement, and pre-public-deployment rate-limit review.
- [ ] Verify tokens never appear in application logs under success or failure.
- [ ] Record the Phase 3 checkpoint only when the complete suite passes.
- **Depends on:** P3-01 through P3-08.
- **Contract coverage:** Auth tests 1–18.

**Phase 3 exit gate:** All 18 Auth Contract test groups pass.

---

## Phase 4A — Customers vertical slice

### P4C-01 — Implement customer schemas and normalization (1 sitting)

- [ ] Model summary/detail/write representations exactly; keep `custom_fields` read-only and returned as `{}`.
- [ ] Trim text, lowercase customer email for consistent contact display/search, and convert permitted optional empty strings to `null`.
- [ ] Enforce every field length/email rule and reject server-managed/unknown fields.
- [ ] Preserve non-unique customer email behavior.
- **Depends on:** Phase 3 gate.
- **Contract coverage:** Customers tests 2, 3, and 12.

### P4C-02 — Implement customer list/search repository (1–2 sittings)

- [ ] Add tenant-scoped list, count, active filter, literal search across name/email/phone, allowed sorting, and pagination.
- [ ] Default lists to active while allowing direct retrieval of inactive customers.
- [ ] Guarantee deterministic `id ASC` tie-breaking and no cross-tenant count leakage.
- [ ] Test composed search/filter cases and literal wildcard handling.
- **Depends on:** P4C-01, P2-10.
- **Contract coverage:** Customers tests 5, 6, 7, 8, 11, and 14.

### P4C-03 — Implement customer create and detail endpoints (1–2 sittings)

- [ ] Implement Administrator/Manager create and all-role tenant-scoped list/detail reads.
- [ ] Return `201`, full representation, canonical `Location`, defaults, and one atomic `customer.create` activity.
- [ ] Return indistinguishable `404` for nonexistent/cross-tenant detail ids.
- [ ] Verify two same-email customers can be created in one tenant.
- **Depends on:** P4C-01, P4C-02, P2-11.
- **Contract coverage:** Customers tests 1, 4, 11, and 12.

### P4C-04 — Implement complete-replacement customer PUT (1–2 sittings)

- [ ] Require every writable field and reject omissions/read-only fields.
- [ ] Support explicit activation/deactivation through `is_active` for Administrator/Manager.
- [ ] Write exactly one transition activity when active state changes, even with other field changes; otherwise write one `customer.update`.
- [ ] Return the full persisted representation.
- **Depends on:** P4C-03.
- **Contract coverage:** Customers test 9.

### P4C-05 — Implement idempotent customer DELETE (1–2 sittings)

- [ ] Deactivate with a tenant-scoped guarded update and inactive-inclusive existence check.
- [ ] Return `204` for first, repeated, and concurrent deactivation of an existing own-tenant customer.
- [ ] Write exactly one `customer.deactivate` record and leave historical booking relationships untouched.
- [ ] Return indistinguishable `404` for nonexistent/cross-tenant ids.
- **Depends on:** P4C-03.
- **Contract coverage:** Customers tests 10 and 11.

### P4C-06 — Complete customer authorization and isolation tests (1 sitting)

- [ ] Prove Staff list/detail access and Staff POST/PUT/DELETE `403 permission_denied` behavior.
- [ ] Exercise missing, invalid, expired, and inactive-account credentials on every customer route.
- [ ] Prove cross-tenant records never appear through lists, searches, counts, detail, PUT, or DELETE.
- [ ] Prove strict query validation on every collection parameter.
- **Depends on:** P4C-02 through P4C-05.
- **Contract coverage:** Customers tests 4, 11, 13, and 14.

### P4C-07 — Complete customer audit atomicity tests (1 sitting)

- [ ] Inject activity insertion failures into create, ordinary update, reactivation, and deactivation.
- [ ] Prove every domain change rolls back completely and no partial response is returned.
- [ ] Verify failed validation/authorization produces no activity record.
- **Depends on:** P4C-03 through P4C-05.
- **Contract coverage:** Customers test 15.

### P4C-08 — Customers contract gate (1 sitting)

- [ ] Run Customers Contract tests 1–15 as one PostgreSQL integration suite.
- [ ] Run the shared conventions completion checklist against the resource.
- [ ] Verify generated OpenAPI matches the approved schemas/status codes.
- [ ] Record the Auth + Customers deployable checkpoint.
- **Depends on:** P4C-01 through P4C-07.
- **Contract coverage:** Customers tests 1–15.

**Phase 4A exit gate:** All 15 Customers Contract test groups pass.

---

## First deployment — immediately after Auth + Customers

### DEP-01 — Build the first deployable backend image (1 sitting)

- [ ] Add a production multi-stage image, non-root runtime user, deterministic dependency install, and startup command.
- [ ] Keep migrations as an explicit release step rather than an uncontrolled multi-instance startup side effect.
- [ ] Expose liveness/readiness and structured logs without secrets.
- **Depends on:** P4C-08.

### DEP-02 — Provision the first remote environment (1–2 sittings)

- [ ] Select the deployment platform now, using the spec's deferred-decision rule.
- [ ] Provision PostgreSQL, configure production environment values, run migrations, and seed a disposable demo tenant.
- [ ] Configure HTTPS and narrowly scoped CORS for the deployed API/docs origin.
- [ ] Record the platform decision and deployment commands.
- **Depends on:** DEP-01.

### DEP-03 — Run deployment smoke and isolation checks (1 sitting)

- [ ] Verify liveness/readiness, login, refresh, `/auth/me`, logout, and complete customer CRUD remotely.
- [ ] Verify one deliberate cross-tenant attempt returns indistinguishable `404` and does not affect counts.
- [ ] Verify migration version, logs, restart persistence, and rollback/redeploy procedure.
- [ ] Add the deployed API URL and known limitations to the README.
- **Depends on:** DEP-02.

**First-deployment gate:** Auth + Customers work remotely. Continue development without waiting for frontend polish.

---

## Phase 4B — Staff and availability

### P4T-01 — Implement staff schemas, normalization, and query repository (1–2 sittings)

- [ ] Implement summary/detail/write schemas without fabricated availability timestamps.
- [ ] Normalize contact fields, preserve permitted duplicates, and enforce all field rules.
- [ ] Add tenant/subset-scoped list, count, search, active filtering, sorting, pagination, and direct inactive reads.
- [ ] Return explicit nullable fields and deterministic ordering.
- **Depends on:** First-deployment gate.
- **Contract coverage:** Staff tests 1–3 and 7–9.

### P4T-02 — Implement staff role scope and `user_id` relationship validation (1–2 sittings)

- [ ] Resolve own-tenant `user_id` body references with inherited indistinguishable `404` behavior.
- [ ] Restrict Staff visibility to all and only staff rows linked to the authenticated user.
- [ ] Return empty list/count for no links and non-enumerating `404` for unlinked detail/availability ids.
- [ ] Enforce Administrator/Manager scalar mutations and Staff scalar `403` behavior.
- **Depends on:** P4T-01, P2-08.
- **Contract coverage:** Staff tests 4, 5, 6, and 16.

### P4T-03 — Implement staff create, list, and detail endpoints (1–2 sittings)

- [ ] Return correct summary/detail shapes, `201`, `Location`, empty availability, and one atomic `staff.create` activity.
- [ ] Support create with all fields and name-only defaults.
- [ ] Apply active/inactive direct-read behavior and role-specific visibility.
- **Depends on:** P4T-01, P4T-02, P2-11.
- **Contract coverage:** Staff tests 1, 5, 6, and 7.

### P4T-04 — Implement complete-replacement staff PUT (1–2 sittings)

- [ ] Require all seven writable fields and revalidate any supplied `user_id` under tenant scope.
- [ ] Support reactivation and mixed-field state changes.
- [ ] Write one transition activity for active-state changes and no extra update activity; write one `staff.update` for non-transition/no-op PUT.
- **Depends on:** P4T-03.
- **Contract coverage:** Staff test 10.

### P4T-05 — Implement idempotent staff DELETE (1–2 sittings)

- [ ] Deactivate with guarded tenant-scoped locking/update behavior.
- [ ] Return `204` on first, repeated, and concurrent deletion while writing exactly one `staff.deactivate` activity.
- [ ] Preserve availability rows and all bookings.
- **Depends on:** P4T-03.
- **Contract coverage:** Staff test 11.

### P4T-06 — Implement availability wall-time parser and validation (1–2 sittings)

- [ ] Validate weekday integer/non-boolean bounds, strict `HH:MM:SS`, start/end ordering, per-day semantics, and maximum input rows.
- [ ] Permit `24:00:00` only as `end_time`; reject `24:00:01` and same-weekday normalization.
- [ ] Add a persistence adapter/value type that round-trips the exact boundary.
- [ ] Return precise indexed field paths for invalid windows.
- **Depends on:** P2-06, P4T-02.
- **Contract coverage:** Staff test 12.

### P4T-07 — Implement availability canonicalization (1 sitting)

- [ ] Sort windows deterministically and coalesce duplicate, overlapping, and touching windows on the same weekday.
- [ ] Preserve separate non-touching windows and different weekdays.
- [ ] Prove canonicalization is idempotent and produces the minimal sorted union.
- **Depends on:** P4T-06.
- **Contract coverage:** Staff test 13.

### P4T-08 — Implement availability GET and atomic replacement PUT (1–2 sittings)

- [ ] Add linked-Staff self-service and Administrator/Manager access.
- [ ] Replace the whole child collection atomically; support initial write, changed replacement, and `[]` clear.
- [ ] Preserve ids and write no activity for canonical no-op; write exactly one `staff.availability.update` for changed state.
- [ ] Roll back the whole replacement if insertion or audit fails.
- **Depends on:** P4T-06, P4T-07, P2-11.
- **Contract coverage:** Staff test 14.

### P4T-09 — Serialize availability and authorization races (1–2 sittings)

- [ ] Lock the staff row before replacement and let the later lock holder replace the complete prior state.
- [ ] Recheck the Staff-to-user link after locking.
- [ ] Race unlink versus self-service replacement and return `404` without mutation when the link is lost.
- [ ] Verify all locks are tenant-scoped and release cleanly on failure.
- **Depends on:** P4T-08.
- **Contract coverage:** Staff test 15.

### P4T-10 — Staff contract gate (1–2 sittings)

- [ ] Run Staff Contract tests 1–18, including cross-tenant, protected-route, strict-query, pagination, and response-shape checks.
- [ ] Verify unavailable colleague identities cannot be resolved through Staff endpoints, matching the Bookings self-only dependency.
- [ ] Verify generated OpenAPI and shared checklist compliance.
- **Depends on:** P4T-01 through P4T-09.
- **Contract coverage:** Staff tests 1–18.

---

## Phase 4B — Services

### P4S-01 — Implement service schemas and boundary validation (1–2 sittings)

- [ ] Normalize name/description and return `custom_fields = {}` as read-only.
- [ ] Accept only integer durations from 1 through 1,440 minutes.
- [ ] Accept price only as canonical fixed-scale decimal strings within the database range; reject JSON numbers and noncanonical strings.
- [ ] Reject client `currency`, active state on POST, server fields, custom fields, and unknown fields.
- **Depends on:** P4T-10.
- **Contract coverage:** Services tests 1–5.

### P4S-02 — Implement service list/search repository (1–2 sittings)

- [ ] Add tenant-scoped literal search over name/description, active filter, all whitelisted sorts/directions, pagination, and deterministic tie-breaker.
- [ ] Default to active while allowing direct inactive reads.
- [ ] Permit all roles to list/detail while preventing cross-tenant list/count leakage.
- **Depends on:** P4S-01, P2-10.
- **Contract coverage:** Services tests 6–10 and 14.

### P4S-03 — Implement service create and detail endpoints (1–2 sittings)

- [ ] Return `201`, canonical `Location`, fixed-scale price, current business currency, defaults, and one atomic `service.create` activity.
- [ ] Support all-fields and description-omitted creation.
- [ ] Permit duplicate names and reject Staff creation.
- **Depends on:** P4S-01, P4S-02, P2-11.
- **Contract coverage:** Services tests 1, 6, and 13.

### P4S-04 — Implement complete-replacement service PUT (1–2 sittings)

- [ ] Require all five writable keys, replace all values, and support reactivation.
- [ ] Write one transition activity for active-state change, otherwise exactly one `service.update`, including a no-op PUT.
- [ ] Derive response currency from the business after the update.
- **Depends on:** P4S-03.
- **Contract coverage:** Services test 11.

### P4S-05 — Implement idempotent service DELETE (1 sitting)

- [ ] Return `204` for first, repeated, and concurrent own-tenant deactivation.
- [ ] Write exactly one `service.deactivate` activity.
- [ ] Preserve all existing booking/payment history.
- **Depends on:** P4S-03.
- **Contract coverage:** Services test 12.

### P4S-06 — Verify currency derivation and booking stability (1–2 sittings)

- [ ] Prove a business-currency change alters returned service currency without converting stored price.
- [ ] Prove duration, price, currency, and active-state changes never rewrite existing booking intervals or historical payments.
- [ ] Complete cross-tenant, duplicate-name, Staff-denial, and inherited-auth tests on every endpoint.
- **Depends on:** P4S-02 through P4S-05.
- **Contract coverage:** Services tests 6, 13, 14, 15, 16, and 17.

### P4S-07 — Services audit and contract gate (1 sitting)

- [ ] Inject audit failures into create, update, transition, and deactivation and prove full rollback.
- [ ] Run Services Contract tests 1–18 and the shared checklist.
- [ ] Verify generated OpenAPI matches canonical decimal-string and derived-currency behavior.
- **Depends on:** P4S-01 through P4S-06.
- **Contract coverage:** Services tests 1–18, especially test 18.

---

## Phase 4C — Administrator user management

### P4U-01 — Finalize the Users API Contract and freeze clarification (1–2 sittings)

- [ ] Define the Administrator-only endpoint set for listing, viewing, creating, complete-replacement updating, role assignment, deactivation, and any permitted reactivation of users.
- [ ] Define normalization, password/bootstrap handling, fixed-role selection, active-state rules, pagination/search/sort, response fields, audit actions, concurrency, and tenant behavior.
- [ ] Document the narrow admin-only global-email `409 duplicate_value` disclosure already reserved by Conventions §3, without revealing the other account's tenant or identity.
- [ ] Explicitly exclude public registration and business creation; business, tenant roles, and initial Administrator remain operations/seed provisioned in the MVP.
- [ ] Add the endpoint-inventory clarification to the Decision Log, then write and accept a numbered automated-test list before implementation.
- **Depends on:** P4S-07.

### P4U-02 — Implement user schemas, role lookup, and repository (1–2 sittings)

- [ ] Implement only the fields and normalization accepted by P4U-01; never expose `password_hash` or accept client `business_id`.
- [ ] Resolve role ids through fixed-name, own-tenant role rows and reject cross-tenant/nonexistent role references without disclosure.
- [ ] Enforce global normalized-email uniqueness and safe `duplicate_value` mapping, including concurrent duplicate attempts.
- [ ] Apply all list/search/sort/count operations under authenticated tenant scope.
- **Depends on:** P4U-01, P2-08 through P2-10.
- **Contract coverage:** The schema, relationship, uniqueness, and collection tests defined by P4U-01.

### P4U-03 — Implement Administrator user-management endpoints and audit (1–2 sittings)

- [ ] Implement the accepted endpoint set with Administrator-only mutation/read scope and the exact contract status/error behavior.
- [ ] Hash initial/replacement credentials using the Auth Contract's password service; never return or log raw credentials.
- [ ] Commit user creation, profile/role/state updates, deactivation/reactivation, and their required activity records atomically.
- [ ] Ensure role changes and deactivation affect the very next protected request because JWTs contain no role/business claims.
- **Depends on:** P4U-02, P2-11, P3-05.
- **Contract coverage:** The endpoint, authorization, audit, and active-state tests defined by P4U-01.

### P4U-04 — Complete user security, tenant, and race coverage (1–2 sittings)

- [ ] Test Administrator/Manager/Staff access for every route and every forbidden method.
- [ ] Test nonexistent/cross-tenant ids and role references, list/count isolation, global duplicate-email behavior, and safe response indistinguishability.
- [ ] Race duplicate creates and conflicting role/state updates; prove deterministic outcomes with no partial user/audit state.
- [ ] Exercise the contract's self-modification safeguards, inactive-account behavior, strict inputs, and audit-failure rollbacks.
- **Depends on:** P4U-03.
- **Contract coverage:** The authorization, isolation, concurrency, and rollback tests defined by P4U-01.

### P4U-05 — Users Contract gate (1 sitting)

- [ ] Run every numbered Users Contract test against PostgreSQL and the shared conventions checklist.
- [ ] Re-run Auth tests proving role changes/deactivation are database-effective on the next request.
- [ ] Verify generated OpenAPI and confirm there is still no registration or business-creation endpoint.
- [ ] Add the accepted Users Contract to the repository's authoritative source list.
- **Depends on:** P4U-01 through P4U-04.
- **Contract coverage:** Complete Users Contract test list.

**Phase 4 exit gate:** Customers, Staff/Availability, Services, and Users contract suites all pass; the first deployment remains healthy.

---

## Phase 5 — Booking engine

### P5-01 — Implement booking schemas and derived interval calculation (1–2 sittings)

- [ ] Implement response/create/complete-replacement schemas with strict UUID/timestamp/notes rules and read-only derived fields.
- [ ] Normalize start time to UTC and derive `end_time` by elapsed minutes from the selected service duration.
- [ ] Reject naive, invalid, and past start timestamps with the contracted field-specific validation response.
- [ ] Never recalculate stored intervals because catalog data changes later.
- **Depends on:** Phase 4 exit gate.
- **Contract coverage:** Bookings tests 1, 2, and 10.

### P5-02 — Implement the booking state machine as a pure service (1–2 sittings)

- [ ] Encode every legal state transition, terminal rule, role permission, and temporal guard from Contract §3.
- [ ] Permit `no_show` at/after `start_time`; keep direct `scheduled → completed` illegal.
- [ ] Distinguish `403 permission_denied` from `409 illegal_status_transition` by the contracted evaluation order.
- [ ] Exhaustively unit-test the transition table before wiring endpoints.
- **Depends on:** P5-01.
- **Contract coverage:** Bookings test 8.

### P5-03 — Implement booking role scope and visibility (1–2 sittings)

- [ ] Give Administrator/Manager tenant-wide scope and Staff self-only scope through all linked staff rows.
- [ ] Permit Staff create only for linked rows, notes updates, and assigned-Staff transitions; deny reschedule, reassignment, and cancellation.
- [ ] Return non-enumerating `404` for Staff-unlinked direct/body staff ids.
- [ ] Implement authenticated `DELETE` as `405 method_not_allowed` with no mutation/audit.
- **Depends on:** P5-01, P4T-02.
- **Contract coverage:** Bookings tests 3, 5, 6, 7, 21, and 22.

### P5-04 — Implement locked reference validation and active-state rules (1–2 sittings)

- [ ] Resolve customer/staff/service body references under tenant scope with inherited indistinguishable `404` behavior.
- [ ] Lock references and return `inactive_resource` for inactive customer/service and `staff_not_bookable` for inactive staff.
- [ ] Allow status/notes-only updates on existing bookings after a referenced resource is later deactivated.
- [ ] Ensure locked service duration is the value used for a new/rescheduled interval.
- **Depends on:** P5-01, P5-03.
- **Contract coverage:** Bookings tests 3, 4, 10, and 18.

### P5-05 — Implement business-local availability containment (1–2 sittings)

- [ ] Map UTC booking intervals into business-local dates/weekdays and materialize the applicable stored windows.
- [ ] Enforce no-rows `staff_not_bookable`, exact boundary containment, and `outside_availability` for gaps/outside windows.
- [ ] Join exact `24:00:00`/next-day `00:00:00` boundaries into continuous cross-midnight availability while preserving real gaps.
- [ ] Keep a single stored row from crossing midnight.
- **Depends on:** P4T-06 through P4T-08, P5-01.
- **Contract coverage:** Bookings tests 11 and 12.

### P5-06 — Implement deterministic DST interval materialization (1–2 sittings)

- [ ] Apply earlier-occurrence start and later-occurrence end for ambiguous local boundaries.
- [ ] Advance nonexistent gap boundaries according to the contract and evaluate containment over unions of real instants.
- [ ] Derive booking duration as elapsed real minutes, not naive wall-clock arithmetic.
- [ ] Test spring-forward, fall-back, and 23/25-real-hour full-day windows in a real IANA zone.
- **Depends on:** P5-05.
- **Contract coverage:** Bookings test 13.

### P5-07 — Implement half-open overlap and blocking-status queries (1–2 sittings)

- [ ] Detect overlap using `existing.start_time < candidate.end_time` and `existing.end_time > candidate.start_time`.
- [ ] Include only scheduled, confirmed, and in-progress bookings as blockers.
- [ ] Permit exact adjacency and release the slot after a transition to completed, cancelled, or no-show commits.
- [ ] Keep every overlap query tenant- and staff-scoped.
- **Depends on:** P5-01, P5-02.
- **Contract coverage:** Bookings tests 14 and 15.

### P5-08 — Implement the canonical booking lock coordinator (1–2 sittings)

- [ ] Apply one global order: booking row on PUT → customer row → staff row(s) in ascending UUID order → service row.
- [ ] Use the staff row as the serialization lock for create/reschedule overlap decisions.
- [ ] Recheck state, visibility, active references, duration, availability, and conflicts after locks are held.
- [ ] Share compatible lock order with availability replacement and staff/customer/service deactivation paths.
- **Depends on:** P5-04 through P5-07.
- **Contract coverage:** Bookings tests 16, 17, and 18.

### P5-09 — Implement `POST /bookings` transaction (1–2 sittings)

- [ ] Execute authorization, canonical locks, reference/active checks, interval derivation, availability, and overlap checks in the contracted order.
- [ ] Insert the scheduled booking and exactly one `booking.create` activity atomically.
- [ ] Return `201`, canonical `Location`, defaults, and full persisted representation.
- [ ] Translate every contracted validation/business/concurrency failure without partial row/audit writes.
- **Depends on:** P5-01 through P5-08.
- **Contract coverage:** Bookings tests 1–7, 11–18, and 23 as applicable to POST.

### P5-10 — Implement complete-replacement `PUT /bookings/{id}` (1–2 sittings)

- [ ] Lock the booking first and enforce role/state restrictions on reassignment/rescheduling/transitions.
- [ ] Reject status combined with customer/staff/service/start-time changes as `422`; require two separately audited calls.
- [ ] Apply the mutually exclusive audit cases: transition, reschedule, or update, exactly one activity per successful call.
- [ ] Recheck all scheduling rules for reference/time changes; permit status + notes with only the transition action.
- **Depends on:** P5-02 through P5-09.
- **Contract coverage:** Bookings tests 7, 8, 9, 10, 17, and 23.

### P5-11 — Implement booking list and detail endpoints (1–2 sittings)

- [ ] Implement overlap-range, staff, customer, service, and status filters independently and jointly.
- [ ] Apply tenant/Staff subset visibility before counts and return empty results for invisible/cross-tenant filter ids without disclosure.
- [ ] Implement every allowed sort/direction, default `-start_time`, deterministic tie-breaker, and pagination.
- [ ] Return indistinguishable `404` for nonexistent/cross-tenant/invisible direct ids.
- **Depends on:** P5-03, P5-09.
- **Contract coverage:** Bookings tests 5, 19, 20, 21, and 22.

### P5-12 — Complete booking audit and rollback coverage (1 sitting)

- [ ] Verify every successful mutation writes exactly one action from the approved vocabulary.
- [ ] Verify failed validation, permission, state, availability, conflict, and method requests write none.
- [ ] Inject audit/domain failures and prove booking row and activity row always commit or roll back together.
- [ ] Verify notes/customer/no-op updates use `booking.update` and reschedules use `booking.reschedule`.
- **Depends on:** P5-09, P5-10.
- **Contract coverage:** Bookings tests 9 and 23.

### P5-13 — Run adversarial booking concurrency suite (1–2 sittings)

- [ ] Race identical/overlapping creates for one staff member and prove one winner with conflict losers.
- [ ] Race create vs reschedule, two reschedules, and transfers between two staff rows.
- [ ] Race availability replacement, staff deactivation, customer/service deactivation, and booking writes.
- [ ] Assert no double booking, deadlock, orphan row, partial audit, or leaked lock after failure.
- **Depends on:** P5-08 through P5-12.
- **Contract coverage:** Bookings tests 16, 17, 18, and 23.

### P5-14 — Booking contract and Phase 5 gate (1–2 sittings)

- [ ] Run Bookings Contract tests 1–23, including exhaustive state, DST, cross-midnight, overlap, tenant, and protected-route coverage.
- [ ] Run all Auth/Customers/Staff/Services regressions with the booking engine enabled.
- [ ] Verify generated OpenAPI, shared checklist compliance, and no `DELETE /bookings/{id}` route.
- [ ] Update the deployed environment and run a salon booking smoke workflow.
- **Depends on:** P5-01 through P5-13.
- **Contract coverage:** Bookings tests 1–23.

**Phase 5 exit gate:** The complete backend core and all five finalized contract suites pass.

---

## Phase 6 — Frontend foundation and core screens

### P6-01 — Scaffold React + TypeScript frontend (1 sitting)

- [ ] Create Vite React TypeScript app with Tailwind CSS and TanStack Query.
- [ ] Configure strict TypeScript, linting, formatting, environment-based API URL, and test tooling.
- [ ] Add the frontend service to local Docker Compose without coupling production builds yet.
- **Depends on:** Phase 5 gate.

### P6-02 — Implement typed API client and auth session lifecycle (1–2 sittings)

- [ ] Generate or maintain types aligned with the approved OpenAPI schemas.
- [ ] Keep access tokens in memory and refresh tokens in `sessionStorage`, never `localStorage`.
- [ ] Implement login, refresh rotation, one-refresh-at-a-time coordination, logout cleanup, and terminal-session handling.
- [ ] Render stable behavior from error codes rather than message text.
- **Depends on:** P6-01, finalized Auth API.

### P6-03 — Implement routing, protected layouts, and role navigation (1–2 sittings)

- [ ] Add login route, protected application shell, loading/expired/inactive/error states, and not-found route.
- [ ] Load `/auth/me` before protected content and derive allowed navigation from the fixed role.
- [ ] Keep authorization server-enforced; UI hiding is convenience only.
- **Depends on:** P6-02.

### P6-04 — Build shared UI primitives and form/error conventions (1–2 sittings)

- [ ] Build accessible buttons, inputs, dialogs, tables, pagination, empty/loading/error states, and confirmation patterns.
- [ ] Map `fields` paths to form controls and preserve a safe general error fallback.
- [ ] Add keyboard/focus behavior and reusable success/error notifications.
- **Depends on:** P6-01, P6-03.

### P6-05 — Build customer screens (1–2 sittings)

- [ ] Add list/search/filter/sort/page, detail, create, complete-replacement edit, deactivate, and reactivate flows.
- [ ] Respect Staff read-only behavior and active/inactive distinctions.
- [ ] Handle duplicate emails as valid data and keep custom fields read-only.
- **Depends on:** P6-04.

### P6-06 — Build staff and availability screens (1–2 sittings)

- [ ] Add Staff list/detail/create/edit/deactivate/reactivate screens according to role.
- [ ] Build whole-week availability replacement with multiple daily windows and exact midnight/day-end presentation.
- [ ] Support linked-Staff self-service without exposing colleague rows.
- [ ] Explain that save canonicalizes overlapping/touching windows.
- **Depends on:** P6-04.

### P6-07 — Build service screens (1–2 sittings)

- [ ] Add list/search/filter/sort/page, detail, create, edit, deactivate, and reactivate flows.
- [ ] Use a decimal-string-safe price input and display the business-derived currency.
- [ ] Enforce duration 1–1,440 in the client while retaining server validation.
- **Depends on:** P6-04.

### P6-08 — Build booking list/calendar and detail/editor flows (2 sittings)

- [ ] Add range/list views, combined filters, status display, detail, creation, rescheduling/reassignment, notes, and permitted transitions.
- [ ] Render controls by role/state but handle authoritative 403/409/422 responses.
- [ ] Keep reschedule/reference changes separate from status changes in the UI.
- [ ] Display times in the business timezone while sending offset-aware timestamps.
- **Depends on:** P6-04, P6-05 through P6-07.

### P6-09 — Build Administrator user-management screen (1–2 sittings)

- [ ] Add the Users & Roles list/detail/create/edit/role-change/deactivate/reactivate flows permitted by the accepted Users Contract.
- [ ] Keep the screen Administrator-only while handling authoritative server denials and global duplicate-email errors safely.
- [ ] Never display password hashes, cross-tenant identity hints, or other sensitive bootstrap data.
- [ ] Add component tests for role changes, inactive users, duplicate email, and forbidden access.
- **Depends on:** P6-04, P4U-05.

### P6-10 — Frontend component and accessibility gate (1–2 sittings)

- [ ] Test protected routing, auth refresh/logout, form field errors, loading/empty/error states, and role-specific controls.
- [ ] Run keyboard, focus, label, contrast, and responsive-layout checks on all core screens.
- [ ] Confirm the frontend never relies on cross-tenant or colleague lookup side effects.
- **Depends on:** P6-02 through P6-09.

**Phase 6 exit gate:** Every core backend workflow has a usable, role-aware frontend path.

---

## Phase 7 — Frontend/backend integration and dashboard

### P7-01 — Finalize the dashboard summary contract (1 sitting)

- [ ] Define tenant-scoped date/filter semantics, response fields, role visibility, timezone rules, and error behavior before coding.
- [ ] Include every frozen §17 dashboard requirement: today's booking count, booking-status summary, active staff count, customer count, today's schedule, and recent activity.
- [ ] Add the accepted contract to the requirements sources.
- **Depends on:** Phase 6 gate.

### P7-02 — Implement dashboard summary endpoint (1–2 sittings)

- [ ] Implement tenant- and role-scoped aggregate queries, today's schedule, and recent-activity retrieval without leaking filtered counts or invisible entities.
- [ ] Apply business-timezone reporting boundaries.
- [ ] Add cross-tenant, empty-data, filter, and authorization tests from the new contract.
- **Depends on:** P7-01.

### P7-03 — Integrate TanStack Query cache behavior (1 sitting)

- [ ] Define stable query keys by resource/filter and invalidate only affected views after mutations.
- [ ] Prevent stale active/inactive and booking-range data after transitions/deactivation.
- [ ] Handle refresh/retry without duplicating unsafe mutations.
- **Depends on:** P6-02, P7-02.

### P7-04 — Build dashboard screen (1 sitting)

- [ ] Render summary cards and operational status breakdown with loading, empty, error, and permission states.
- [ ] Keep reports to dashboard scope; do not pull Phase 9 billing into MVP core.
- **Depends on:** P7-02, P7-03.

### P7-05 — Add browser-level core workflow tests (1–2 sittings)

- [ ] Cover Administrator login → create/role-assign a user → customer → staff/availability → service → booking → transition → logout.
- [ ] Cover Staff self-only workflow and Manager/Admin workflow.
- [ ] Cover one deliberate forbidden action, one conflict, one expired-session refresh, and one cross-tenant API attempt.
- [ ] Run against the real PostgreSQL-backed application.
- **Depends on:** P7-03, P7-04.

### P7-06 — Deploy the complete hard-coded salon vertical slice (1 sitting)

- [ ] Deploy frontend/backend together and run P7-05 smoke subset remotely.
- [ ] Confirm HTTPS, CORS, environment separation, migration version, and restart persistence.
- [ ] Capture the first working-demo checkpoint before starting configuration work.
- **Depends on:** P7-05.

**Phase 7 exit gate:** The hard-coded Demo Salon works end to end in the deployed environment.

---

## Phase 8 — Business configuration, modularity, and repair-shop reskin

### P8-01 — Finalize configuration API/schema contract (1–2 sittings)

- [ ] Define business profile, terminology labels, module flags, custom-field definitions, language/currency/timezone settings, authorization, audit, and validation.
- [ ] Explicitly amend the earlier customer/service `custom_fields` write freeze through the conventions exception mechanism.
- [ ] Define timezone-change warnings/confirmation and the effect on wall-clock availability.
- [ ] Record material decisions before migration/code.
- **Depends on:** Phase 7 gate.

### P8-02 — Add configuration migrations and models (1–2 sittings)

- [ ] Implement only the fields/tables accepted by P8-01 and the authoritative schema update.
- [ ] Preserve existing hard-coded salon data through migration.
- [ ] Add DB constraints/indexes and clean replay tests.
- **Depends on:** P8-01.

### P8-03 — Implement configuration and module APIs (1–2 sittings)

- [ ] Add tenant-scoped read/update behavior, fixed-role authorization, audit, and optimistic/concurrency behavior from the contract.
- [ ] Keep disabled modules inaccessible server-side, not merely hidden in the UI.
- [ ] Test cross-tenant references and rollback on audit failure.
- **Depends on:** P8-02.

### P8-04 — Implement configured custom-field validation (1–2 sittings)

- [ ] Validate customer/service custom-field keys, types, requiredness, enum/range/length rules, and removal/change behavior against active definitions.
- [ ] Define safe handling of historical values when definitions change.
- [ ] Add API and persistence tests for both valid and invalid profile data.
- **Depends on:** P8-03.

### P8-05 — Build Settings and terminology/module UI (1–2 sittings)

- [ ] Add role-restricted settings screens for labels, module flags, custom-field definitions, currency, and timezone.
- [ ] Apply configured labels throughout navigation, forms, empty states, and validation messages.
- [ ] Add the English-only language selector state without pretending additional translations exist.
- **Depends on:** P8-03, P8-04.

### P8-06 — Implement and verify Repair Shop reskin (1–2 sittings)

- [ ] Seed/configure Customer → Technician → Job → Repair Service terminology without code branching by tenant.
- [ ] Demonstrate custom fields appropriate to repair work.
- [ ] Run the same core customer/staff/service/booking workflows under both profiles.
- **Depends on:** P8-05.

### P8-07 — Phase 8 regression gate (1–2 sittings)

- [ ] Run all five original contract suites and prove configuration did not change their default behavior unexpectedly.
- [ ] Run new configuration/custom-field/module/timezone tests and both demo-profile browser flows.
- [ ] Verify inactive, tenant, audit, and strict-input rules remain consistent.
- **Depends on:** P8-01 through P8-06.

**Phase 8 exit gate:** One codebase supports the Salon and Repair Shop profiles through stored configuration.

---

## Phase 9 — Stretch: payments and basic reports

### P9-00 — Apply the stretch gate (1 sitting)

- [ ] Start Phase 9 only if Phases 1–8 are deployed, stable, and documented.
- [ ] If the gate is not met, mark Phase 9 deferred without affecting MVP completion.

### P9-01 — Finalize the payments contract (1–2 sittings)

- [ ] Define create/read/refund/status behavior, role permissions, multiple-payment/no-allocation model, stored currency, audit, tenant scoping, and inactive-reference behavior.
- [ ] Register any new error codes without repurposing shipped codes.
- [ ] Define required automated tests before implementation.
- **Depends on:** P9-00 passed.

### P9-02 — Implement payment API and tests (1–2 sittings)

- [ ] Use the existing authoritative payment table unless P9-01 requires an accepted schema revision.
- [ ] Preserve historical amount/currency and append-only financial behavior.
- [ ] Implement contract tests, audit atomicity, tenant isolation, and booking-reference validation.
- **Depends on:** P9-01.

### P9-03 — Add payment UI and basic reporting (1–2 sittings)

- [ ] Add payment recording/history/refund controls and minimal reports defined by P9-01.
- [ ] Keep payment totals explicit about payment date versus booking/service date.
- [ ] Add browser workflow tests.
- **Depends on:** P9-02.

**Phase 9 exit gate:** Optional. Its deferral does not block MVP completion.

---

## Phase 10 — Testing, security, and accessibility hardening

### P10-01 — Run dependency and secret security review (1 sitting)

- [ ] Scan pinned dependencies and container images; resolve actionable high/critical findings.
- [ ] Scan repository/history for secrets and unsafe example credentials.
- [ ] Document accepted residual risks rather than hiding them.

### P10-02 — Harden HTTP security and abuse controls (1–2 sittings)

- [ ] Review HTTPS enforcement, trusted hosts/proxies, CORS, security headers, body-size limits, and log redaction.
- [ ] Implement and test login/refresh rate limiting if public exposure warrants it, using the reserved `429 rate_limited` behavior.
- [ ] Re-run JWT/password/token adversary tests.
- **Depends on:** P10-01.

### P10-03 — Run authorization and tenant-isolation regression campaign (1–2 sittings)

- [ ] Generate a route/role matrix and test every protected method.
- [ ] Attempt cross-tenant ids through paths, bodies, filters, counts, locks, and races.
- [ ] Verify indistinguishable responses and absence of timing/log disclosure where practical.
- **Depends on:** P10-02.

### P10-04 — Complete accessibility and responsive pass (1–2 sittings)

- [ ] Check WCAG 2.2 AA-relevant labels, keyboard access, focus, contrast, error association, tables, dialogs, and status announcements.
- [ ] Test core screens at phone, tablet, and desktop widths.
- [ ] Add automated checks plus a documented manual checklist.

### P10-05 — Run performance and concurrency regression (1–2 sittings)

- [ ] Profile list/search/filter/count queries against realistic demo volume and verify required indexes are used.
- [ ] Stress refresh/logout, deactivation, availability replacement, and booking conflict/reschedule races.
- [ ] Confirm bounded response times, no pool leaks, no deadlocks, and stable conflict mapping.

### P10-06 — Full regression and release-quality gate (1 sitting)

- [ ] Run backend unit/integration/concurrency/DST suites and frontend component/browser suites.
- [ ] Review coverage by contract requirement, not only percentage.
- [ ] Eliminate flaky tests or document/repair their deterministic dependencies.
- **Depends on:** P10-01 through P10-05.

---

## Phase 11 — Docker and production configuration polish

### P11-01 — Optimize production images and Compose profile (1 sitting)

- [ ] Minimize image size/attack surface, pin base images, run non-root, and add health checks.
- [ ] Separate development conveniences from production configuration.
- [ ] Verify reproducible builds.

### P11-02 — Finalize production settings and secret handling (1 sitting)

- [ ] Validate required secrets, database TLS, proxy settings, CORS origins, issuer/audience, and environment-specific logging.
- [ ] Document rotation procedures for JWT/database credentials.
- [ ] Confirm no production secret falls back to a development default.

### P11-03 — Add structured observability (1–2 sittings)

- [ ] Add request correlation ids, safe structured logs, latency/status metrics, and important domain/security event logging.
- [ ] Exclude passwords, tokens, sensitive notes, and unnecessary customer data.
- [ ] Add a short investigation guide for auth failures, booking conflicts, and migration issues.

### P11-04 — Write database backup and migration runbook (1 sitting)

- [ ] Document backup, restore verification, pre-migration backup, migration execution, failure response, and rollback limits.
- [ ] Perform one restore rehearsal in a disposable environment.

---

## Phase 12 — Deployment hardening and demo operations

### P12-01 — Finalize liveness, readiness, and startup behavior (1 sitting)

- [ ] Keep liveness process-only and readiness dependency-aware.
- [ ] Ensure migration mismatch or unavailable database prevents readiness without leaking details.
- [ ] Test graceful shutdown and connection cleanup.

### P12-02 — Build repeatable demo data lifecycle (1 sitting)

- [ ] Create deterministic, clearly fictional Salon and Repair Shop demo data.
- [ ] Document safe reset/reseed without touching production tenants.
- [ ] Avoid healthcare or real personal data.

### P12-03 — Rehearse production deployment and recovery (1–2 sittings)

- [ ] Deploy from a clean revision, migrate, smoke test, restart, roll forward, and exercise the documented recovery path.
- [ ] Verify backups, health checks, logs, HTTPS, and both profile workflows.
- [ ] Record actual limitations of the selected free/low-cost platform.

### P12-04 — Complete operator and deployment documentation (1 sitting)

- [ ] Document environment variables, deploy steps, migrations, health endpoints, backup/restore, demo reset, known limitations, and troubleshooting.
- [ ] Ensure a reviewer can deploy without private verbal instructions.

---

## Phase 13 — Portfolio polish and release

### P13-01 — Finalize README and architecture narrative (1–2 sittings)

- [ ] Explain the problem, target domains, scope boundaries, stack, modular-monolith design, multi-tenancy, authorization, concurrency, DST handling, and configuration approach.
- [ ] Include setup, tests, deployment, demo credentials, security limitations, and project status.

### P13-02 — Produce architecture and workflow diagrams (1 sitting)

- [ ] Add concise system/container, data-model, auth lifecycle, and booking lock/validation-flow diagrams.
- [ ] Keep editable sources beside rendered exports.

### P13-03 — Capture screenshots and demonstration script (1 sitting)

- [ ] Capture clean responsive screens for both profiles and core role workflows.
- [ ] Write a five-minute demo script: website/app login → configure resources → book → conflict → transition → dashboard.

### P13-04 — Write portfolio case study and update CV (1–2 sittings)

- [ ] Explain constraints, key decisions, trade-offs, difficult bugs, testing strategy, deployment, and measurable outcomes.
- [ ] Link repository and live demo; avoid claiming unbuilt/stretch features.
- [ ] Update CV once the deployed demo is stable, as required by the specification.

### P13-05 — Tag the MVP release (1 sitting)

- [ ] Run the final acceptance checklist, full regression, clean setup, deployment smoke, and demo script.
- [ ] Confirm no open blocker is mislabeled as polish.
- [ ] Tag the release and record deferred work separately.

**MVP completion gate:** The deployed, documented, tested Salon + Repair Shop system meets the overall Definition of Done. Phase 9 may remain deferred.

---

## Phase 14 — Explicitly deferred

- [ ] Do **not** build the public booking flow, embeddable widget, or marketing website in this repository during the MVP.
- [ ] Start Project #2 only after the BMS is deployed and working, using its own repository, contract, deployment, README, and case study.

---

## 4. Contract-test traceability matrix

This matrix is the audit trail that prevents a test requirement from being lost when issues are created. A test may map to more than one task because some requirements cross validation, authorization, persistence, and concurrency boundaries.

### Authentication Contract

| Contract tests | Primary backlog tasks |
|---|---|
| 1–2 | P3-01, P3-02, P3-03 |
| 3–5 | P3-02, P3-04, P3-08 |
| 6–7 | P3-05, P3-07 |
| 8–10 | P3-06 |
| 11–14 | P2-09, P3-01, P3-03, P3-07 |
| 15 | P3-08 |
| 16–17 | P3-01, P3-03, P3-04 |
| 18 | P3-08 |
| Complete gate | P3-09 |

### Customers Contract

| Contract tests | Primary backlog tasks |
|---|---|
| 1 | P4C-03 |
| 2–3 | P4C-01 |
| 4 | P4C-03, P4C-06 |
| 5–8 | P4C-02 |
| 9 | P4C-04 |
| 10 | P4C-05 |
| 11 | P4C-02, P4C-03, P4C-05, P4C-06 |
| 12 | P4C-01, P4C-03 |
| 13–14 | P2-09, P4C-06 |
| 15 | P4C-07 |
| Complete gate | P4C-08 |

### Staff Contract

| Contract tests | Primary backlog tasks |
|---|---|
| 1–3 | P4T-01, P4T-03 |
| 4 | P4T-02 |
| 5–6 | P4T-02, P4T-03 |
| 7–9 | P4T-01, P4T-03 |
| 10 | P4T-04 |
| 11 | P4T-05 |
| 12 | P4T-06 |
| 13 | P4T-07 |
| 14 | P4T-08 |
| 15 | P4T-09 |
| 16–18 | P2-09, P4T-02, P4T-10 |
| Complete gate | P4T-10 |

### Services Contract

| Contract tests | Primary backlog tasks |
|---|---|
| 1–5 | P4S-01, P4S-03 |
| 6 | P4S-02, P4S-03, P4S-04, P4S-05 |
| 7–10 | P4S-02 |
| 11 | P4S-04 |
| 12 | P4S-05 |
| 13–17 | P4S-02, P4S-03, P4S-06 |
| 18 | P4S-07 |
| Complete gate | P4S-07 |

### Users Contract — to be finalized by P4U-01

| Contract area | Primary backlog tasks |
|---|---|
| Endpoint set, permissions, active state, password/bootstrap policy, audit vocabulary, numbered tests | P4U-01 |
| Schemas, tenant-owned role references, collection behavior, global email uniqueness | P4U-02 |
| Administrator endpoints, password hashing, role/state immediacy, atomic audit | P4U-03 |
| Authorization, tenant isolation, concurrency, self-modification rules, rollback | P4U-04 |
| Complete contract gate and Auth regression | P4U-05 |
| Administrator frontend workflow | P6-09, P7-05 |

### Bookings Contract

| Contract tests | Primary backlog tasks |
|---|---|
| 1–2 | P5-01, P5-09, P5-10 |
| 3–4 | P5-03, P5-04 |
| 5–7 | P5-03, P5-09, P5-10, P5-11 |
| 8 | P5-02, P5-10 |
| 9 | P5-10, P5-12 |
| 10 | P5-01, P5-04 |
| 11–12 | P5-05 |
| 13 | P5-06 |
| 14–15 | P5-07 |
| 16–18 | P5-04, P5-08, P5-09, P5-13 |
| 19–20 | P5-11 |
| 21–22 | P5-03, P5-11 |
| 23 | P5-09, P5-10, P5-12, P5-13 |
| Complete gate | P5-14 |

## 5. Phase 0 closure checklist

- [x] Decision Log finalized for Phase 0 decisions.
- [x] Authoritative DBML ERD finalized.
- [x] Shared API Conventions finalized.
- [x] Authentication Contract finalized.
- [x] Customers Contract finalized.
- [x] Staff/Availability Contract finalized.
- [x] Services Contract finalized.
- [x] Bookings Contract finalized.
- [x] Permission matrix and acceptance criteria finalized in the specification.
- [x] Section 55.1 converted into this ordered, test-traceable implementation backlog.

**Phase 0 declared COMPLETE on 2026-08-16, thirteen days ahead of the 29 August timebox. The next unchecked task is P1-01.**
