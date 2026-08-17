---
paths:
  - "backend/app/**/*.py"
  - "backend/scripts/**/*.py"
  - "scripts/**/*.py"
---

# Backend Python rules

## Layering

Requests flow `endpoint → service → repository → session`. Do not skip a layer.

- **Endpoints** parse, authorize, and serialize. No SQL, no business rules.
- **Services** own business rules and transaction boundaries. A service opens the unit of work; the
  domain mutation and its required activity-log insert commit together or not at all.
- **Repositories** own queries. A repository never commits inside a multi-row business operation.
- **Schemas** (Pydantic) are the boundary. Models (SQLAlchemy) never leave the service layer.

## Tenant scoping

Use the centralized tenant-scoped helpers from `app/db/` — do not write a raw `select()` against a
tenant-owned table in an endpoint or service. Every read, count, existence check, relationship
validation, `SELECT ... FOR UPDATE`, insert, and update filters on the authenticated
`business_id` in the statement itself.

Cross-tenant and nonexistent ids are indistinguishable: `404 not_found`, same body, same timing
characteristics where practical. This applies to ids in the path, in query filters, and inside
request bodies.

## Validation and errors

- Reject unknown body fields and unknown query parameters. Pydantic models forbid extras.
- Malformed UUIDs, unsupported content types, and disallowed repeated query parameters get the
  contracted error, not a framework default.
- Raise the project's typed domain errors. The middleware maps them to the shared error envelope.
  Never `raise HTTPException(detail=...)` with a raw string in a domain path.
- Never let a `500` carry a stack trace, exception message, SQL fragment, or table name.

## Types and money and time

- Type-annotate every function signature. No bare `Any` on a public boundary.
- Money is a fixed-scale `Decimal` and serializes as a canonical decimal **string**. Never a JSON
  float. Never round in Python where the database has the authority.
- Timestamps are timezone-aware UTC in storage and transport. Reject naive datetimes at the boundary.
- Availability wall-times are **not** instants. `24:00:00` is a legal `end_time` and must round-trip
  exactly; never normalize it to `00:00:00` on the same weekday.
- Booking `end_time` is derived from the locked service duration. It is never client-supplied and
  never recomputed because catalog data changed later.

## Secrets and logging

- Configuration comes from typed settings only. No `os.getenv` scattered through modules, no
  hardcoded defaults for production values.
- Structured logs with a request id. Never log a password, raw or hashed token, JWT, `Authorization`
  header, booking note, or full customer record.

## Style

Ruff formats and lints; the config in `backend/pyproject.toml` wins over your preference. Prefer
explicit over clever. Add a comment only for a non-obvious *why* — never to restate the code.
