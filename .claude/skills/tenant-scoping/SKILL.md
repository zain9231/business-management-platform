---
name: tenant-scoping
description: The multi-tenancy rules — how to scope every query, how nonexistent and cross-tenant ids must be indistinguishable, and the role visibility subsets. Use whenever writing a repository query, a service, an endpoint, or an isolation test.
---

# Tenant scoping

**Not authoritative.** `docs/api/shared-api-conventions.md`, the endpoint contracts, and
`docs/architecture/erd/source/business-management-platform-erd-v1.2.dbml` are. This is the checklist.

## The rule

Tenant scoping lives **in the SQL statement**, never in a Python check after an unscoped fetch. This
applies to reads, writes, counts, existence checks, relationship validation, row locks, inserts, and
updates — with no exception for "internal" helpers.

Use the centralized tenant-scoped helpers. If you find yourself writing a bare `select()` against a
tenant-owned table, stop: either the helper exists and you missed it, or the helper needs extending.

The authenticated `business_id` comes from the user's own database row, loaded on every protected
request. It never comes from a request body, a query parameter, a header, or a JWT claim — access
tokens carry identity only.

## Indistinguishability

Nonexistent and cross-tenant must produce a **byte-identical** `404 not_found`. This holds for:

- an id in the path
- an id in a query filter — returns empty results, not an error that confirms existence
- an id inside a request body (customer, staff, service, role, user references) — inherits the same
  `404`, never a `422` or a `409` that reveals the reference exists
- counts and pagination totals — never reflect another tenant's rows

The single permitted exception is the narrow Administrator-only global-email `409 duplicate_value`
reserved by the conventions, which must reveal neither the other tenant nor the other account.

## Role visibility subsets

Tenant scope is the outer boundary; role scope narrows it further. Both apply.

- **Administrator / Manager** — tenant-wide.
- **Staff, on staff and booking endpoints** — self-only, resolved through **all** staff rows linked to
  the authenticated user. Staff see all and only their own linked rows; an unlinked staff id returns a
  non-enumerating `404`, including for detail reads and availability. Colleague identities must not be
  resolvable through staff or booking endpoints.
- **Staff, on customers and services** — full tenant-scoped read, no writes. Customers: the accepted
  Decision Log clarification of 2026-08-16 gives Staff full read on `GET /customers` and
  `GET /customers/{id}`. Services: Staff have full read on both endpoints. Neither is self-only.

Staff may create bookings only for linked rows, may update notes, and may perform assigned-staff
transitions. Staff may not reschedule, reassign, or cancel.

## Negative tests are mandatory

Every tenant-scoped helper and every endpoint needs a deliberate cross-tenant attempt through the
path, a filter, and the request body. An implementation without those tests is not done, regardless
of whether the positive tests pass.

To sweep an existing implementation, run the `tenant-isolation-auditor` subagent.
