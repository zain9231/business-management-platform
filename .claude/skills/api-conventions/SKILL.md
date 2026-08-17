---
name: api-conventions
description: Navigate the shared API conventions when implementing or reviewing any endpoint — error envelope, error codes, strict input, pagination, sorting, filtering, literal search, and audit vocabulary. Use whenever writing an endpoint, schema, repository query, or contract test.
---

# Shared API conventions — how to use them

**This skill is not authoritative.** `docs/api/shared-api-conventions.md` (FINAL, Revision 3) is.
Read the relevant section there before implementing. This file tells you which section to read and
which traps to check.

## Where things live

| You are implementing | Read |
|---|---|
| Error responses, error codes, validation shape | §§3–5 |
| Pagination, filtering, sorting | §§6–8 |
| Audit / activity vocabulary | §9 |
| Strict input, deterministic response rules | §12 |

Endpoint-specific fields, permissions, filters, and transitions are **not** here — they are in the
resource's own file under `docs/api/contracts/`. When the two appear to disagree, the endpoint
contract owns endpoint behavior and the conventions own cross-cutting behavior; a real contradiction
is a Decision Log matter, not something to resolve in code.

## Traps that cost the most time

- **The envelope is the only response shape.** Never let FastAPI's `{"detail": ...}` reach a client.
  Framework validation errors, `HTTPException`, authentication failures, and unhandled exceptions are
  all remapped by the middleware.
- **Error codes are a closed registry.** Use an existing code — including `inactive_resource`. Never
  invent one, never repurpose a shipped one. A new code requires its own contract acceptance.
- **Evaluation order is contracted.** `403 permission_denied` versus `409 illegal_status_transition`
  is decided by the order the contract specifies, not by whichever check happens to run first.
- **Strict input means both directions.** Reject unknown body fields *and* unknown query parameters,
  plus malformed UUIDs, unsupported content types, and disallowed repeated query parameters.
- **Sorting is whitelisted and deterministic.** Only listed fields, and always an `id ASC`
  tie-breaker so duplicate sort values page stably.
- **Literal search is literal.** Escape `%`, `_`, and the configured `LIKE` escape character before
  the query. A user searching for `50%` must not match everything.
- **Ranges are half-open.** `[start, end)` everywhere, including booking overlap.
- **Audit strings are centrally validated.** `customer.create`, `booking.reschedule`,
  `staff.availability.update`, and the rest come from one validated vocabulary. Exactly one row per
  successful mutation, zero on any failure, and it commits in the same transaction as the mutation.
- **Deterministic responses.** Same request, same state, same bytes. No incidental ordering, no
  timestamp jitter in a field the contract says is stable.

## Before calling an endpoint done

Walk the conventions completion checklist against the resource. `/contract-gate <resource>` does this
as part of the full gate.
