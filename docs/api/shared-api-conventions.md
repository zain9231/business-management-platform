# Shared API Conventions — Business Management Platform

**Phase 0 artifact.** Defined once and reused by every endpoint contract: authentication, customers, staff, services, bookings, and all later phases. Based on Specification v1.2 Sections 15, 18, 19, 45, 47, and 48. Status: **FINAL — Revision 3** — verified through the complete Phase 0 contract set on 2026-08-16.

---

## 1. Artifact Authority and Precedence

- For every project artifact, the editable source is authoritative. PDF, image, and other rendered exports are presentation copies and may omit source-only notes, metadata, constraints, indexes, checks, deletion rules, or other non-rendered details.
- The DBML source is the authoritative database/ERD definition. The ERD PDF is a visual export only.
- Accepted entries in the Specification Decision Log override contradictory text in earlier specification sections or summary tables.
- This document is authoritative for shared, cross-cutting API behavior. An individual endpoint contract is authoritative for that endpoint's fields, permissions, filters, transitions, and other endpoint-specific behavior.
- Endpoint contracts must not silently contradict these conventions. Any necessary exception must be explicit and justified in the contract; a material architectural change must also be recorded in the Decision Log.
- Generated OpenAPI documentation must match the approved contracts but does not replace them as the requirements source.

## 2. General

- **Base path:** All MVP application endpoints use `/api/v1`, including authentication endpoints. The separate `/public/{slug}/…` namespace is reserved for the future public booking API (Specification Section 58) and is not implemented in the MVP.
- **Format:** Request and response bodies use JSON encoded as UTF-8. JSON responses use `Content-Type: application/json`. A `204 No Content` response has no body.
- **Field naming:** `snake_case` everywhere.
- **Resource naming:** Plural or established collection nouns, for example `/customers`, `/bookings`, and `/staff`.
- **Identifiers:** UUIDs in all paths and bodies. Raw database integers never appear in the API.
- **Timestamps:** Clients must send ISO 8601 timestamps with an explicit UTC offset. Naive timestamps are rejected. The server normalizes timestamps to UTC and serializes them using `Z`, for example `2026-08-29T14:30:00Z`.
- **Availability times:** `staff_availability.start_time` and `end_time` are the only timestamp-rule exception. They are business-local wall-clock times serialized as `HH:MM:SS`; `weekday` uses `0 = Monday` through `6 = Sunday`.
- **Authentication:** Protected endpoints require `Authorization: Bearer <access_token>`. Endpoints are protected unless their individual contract explicitly marks them unauthenticated. Login and refresh are expected unauthenticated exceptions; logout and `/auth/me` are defined by the authentication contract.
- **Strict inputs:** Unknown JSON body fields and unknown query parameters are rejected with `422 validation_error`. Pydantic request models use `extra="forbid"` or equivalent behavior.
- **Normalization:** Contracts define field-specific normalization. At minimum, leading/trailing whitespace is removed where appropriate and user email addresses are normalized to lowercase before uniqueness checks and storage.

## 3. Tenant and Account Rules

- The server derives tenant context exclusively from the authenticated principal. `business_id` is never accepted from the client for authorization purposes—not in paths, request bodies, or query parameters.
- Every tenant-owned lookup, relationship validation, list, count, and mutation is scoped to the authenticated tenant.
- Tenant ownership should be enforced in the database query itself, for example with both `id` and `business_id`, rather than by loading an unscoped record and checking it afterward.
- A resource that does not exist and a resource belonging to another tenant both return `404 not_found`. Cross-tenant existence must not be inferable through status, response body, or a meaningfully different error path.
- A nonexistent or cross-tenant tenant-owned entity referenced by id in a request body returns the same `404 not_found`; malformed identifiers remain `422 validation_error`. Whether an existing reference is active or otherwise usable is a separate endpoint-specific business-rule check.
- Global user-email uniqueness creates one narrow, deliberate MVP exception: an authorized tenant administrator attempting to create a user may learn only that an email address is unavailable through `409 duplicate_value`. The response must not reveal the other account's tenant, status, role, name, or any other details. The users contract must document this admin-only trade-off explicitly.
- Protected-request authentication/authorization must reject inactive users and inactive businesses. The authentication contract defines the precise token and error behavior.
- Automated tests must include deliberate cross-tenant reads, writes, relationship references, filters, counts, and deactivation attempts.

## 4. Status Codes

| Code | Meaning | Used for |
|---|---|---|
| `200` | OK | Successful reads and updates |
| `201` | Created | Successful creation; body contains the created resource and `Location` identifies its canonical endpoint |
| `204` | No Content | Successful deactivation or logout where no response body is useful |
| `400` | Bad Request | Request-level failure explicitly documented by a contract and not represented by schema validation; not used for ordinary FastAPI validation |
| `401` | Unauthorized | Missing, invalid, expired, or revoked authentication credential, as applicable to the endpoint |
| `403` | Forbidden | Identity is authenticated but use is prohibited, including role/permission denial within the tenant or an inactive account with an otherwise valid access token |
| `404` | Not Found | Resource does not exist or is outside the authenticated tenant |
| `405` | Method Not Allowed | Path exists but does not support the requested HTTP method |
| `409` | Conflict | Valid request conflicts with current state or a business rule, such as overlap, unavailable time, illegal transition, or duplicate unique value |
| `415` | Unsupported Media Type | Endpoint requires JSON but receives an unsupported request content type |
| `422` | Unprocessable Entity | Invalid JSON or path, query, or body validation failure, including malformed UUIDs and unknown fields |
| `429` | Too Many Requests | Rate limit or login-abuse control triggered, if implemented |
| `500` | Internal Server Error | Unexpected server failure; response never exposes internals |

`401` responses include `WWW-Authenticate: Bearer` where applicable.

Rule of thumb: `422` means the submitted representation is invalid; `409` means the representation is valid but conflicts with current application state.

## 5. Error Format

All error responses use one envelope:

```json
{
  "error": {
    "code": "booking_conflict",
    "message": "The requested time is no longer available.",
    "fields": [
      {
        "field": "body.start_time",
        "message": "This time overlaps an existing booking."
      }
    ]
  }
}
```

- `code` is stable, machine-readable, and `snake_case`. Frontend logic keys on `code`, never on `message` text.
- `message` is human-readable and safe to display. It must not reveal secrets, cross-tenant information, database details, stack traces, or whether one part of a credential was correct.
- `fields` is optional. It may be included for validation or business-rule errors that can be associated with specific inputs and is omitted when it adds no value.
- Field paths use `body.<field>`, `query.<parameter>`, or `path.<parameter>` notation, with dotted or indexed continuation for nested data.
- Authentication failures use safe messages such as “Invalid email or password” rather than revealing whether an account exists.
- The authentication contract determines where token-specific codes are exposed. Access-token handling may distinguish `token_expired` when the client can safely attempt refresh. The refresh endpoint does not distinguish unknown, expired, revoked, or previously rotated refresh tokens to the caller; those cases use the same safe `401 invalid_token` response even though the server may record the internal reason securely.
- Unexpected failures return `500 internal_error` with a generic message; detailed diagnostics go only to protected application logs.

**Initial error-code registry** — extend it as contracts are written, but never rename or repurpose a shipped code:

`validation_error` · `malformed_request` · `invalid_credentials` · `authentication_required` · `invalid_token` · `token_expired` · `token_revoked` · `not_found` · `permission_denied` · `booking_conflict` · `outside_availability` · `staff_not_bookable` · `inactive_resource` · `illegal_status_transition` · `duplicate_value` · `inactive_account` · `method_not_allowed` · `unsupported_media_type` · `rate_limited` · `internal_error`

`inactive_resource` is a `409` business-rule conflict, currently used by the Bookings contract when a tenant-owned customer or service reference exists and is visible but inactive, so it cannot be selected for a new or rescheduled booking. Other contracts may reuse the code when an existing, visible referenced entity is inactive and that state prevents the requested operation. It is distinct from `404 not_found` (missing or cross-tenant reference) and from `staff_not_bookable` (inactive staff or missing staff availability).

FastAPI, Starlette, authentication, and application exceptions are remapped to this envelope by centralized handlers. Framework-default `{"detail": ...}` responses must not escape from production endpoints.

## 6. Pagination

Collection endpoints use page-based pagination:

```text
?page=1&page_size=25
```

- `page` is 1-based and must be at least `1`.
- `page_size` defaults to `25` and must be between `1` and `100` inclusive.
- Collection endpoints are never unbounded unless an individual contract explicitly documents a genuinely bounded child collection.
- A page beyond the available results returns an empty `data` array, not `404`.
- When `total_items` is `0`, `total_pages` is `0`.

Response envelope:

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "page_size": 25,
    "total_items": 0,
    "total_pages": 0
  }
}
```

Single-resource endpoints return the resource directly without a `data` envelope.

Pagination queries must use deterministic ordering. The documented sort is followed by `id` as a final tie-breaker, for example `name ASC, id ASC`.

## 7. Filtering and Search

- Filters are query parameters named after the field, for example `?status=confirmed&staff_id=<uuid>`.
- Range filters use `_from` and `_to` suffixes with half-open semantics: `field >= *_from` and `field < *_to`.
- Example full-August range: `?start_time_from=2026-08-01T00:00:00Z&start_time_to=2026-09-01T00:00:00Z`.
- Each endpoint contract states the exact range meaning. In particular, the booking contract must state whether a time range selects bookings that start within the range or bookings that overlap the range; calendar views normally require overlap behavior.
- Text search uses one `?search=` parameter. Each contract states the matched fields and normalization behavior. Customer search matches name, email, and phone per Specification Section 18.
- `?is_active=true|false` applies only to resources that contain `is_active`. Collection endpoints for those resources default to `is_active=true`.
- Authorized direct `GET /{id}` lookups may return inactive records. The collection default does not turn an existing inactive resource into `404`.
- Unknown, repeated where disallowed, or malformed filter parameters return `422 validation_error` rather than being silently ignored.

## 8. Sorting

- `?sort=field` sorts ascending and `?sort=-field` sorts descending, for example `?sort=-start_time`.
- The MVP accepts exactly one client-selected sort field. Comma-separated sorts, repeated `sort` parameters, or any other multi-field syntax return `422 validation_error`. The server-added `id` tie-breaker is not considered a second client-selected field.
- Each endpoint contract whitelists sortable fields. Unsupported sort fields return `422 validation_error`.
- Every collection contract documents its default sort, for example bookings by `-start_time` and customers by `name`.
- The server always appends `id` in a consistent direction as a stable tie-breaker unless `id` is already part of the requested sort.
- Contracts containing nullable sortable fields must define their null-ordering behavior.

## 9. Write Semantics

- `POST` create returns `201`, the full persisted resource, and its canonical `Location` header. The response includes server-generated and server-derived values such as `id`, timestamps, and booking `end_time`.
- `PUT /{id}` is a complete replacement of all client-writable fields. Required writable fields omitted from the request return `422 validation_error`.
- Read-only or server-derived fields—including `id`, `business_id`, `created_at`, `updated_at`, and booking `end_time`—are rejected with `422 validation_error` if supplied in a write request unless an individual contract explicitly defines otherwise.
- Unknown body fields are rejected with `422 validation_error`; they are never silently ignored.
- `DELETE` on soft-delete resources—customers, staff, services, and users—sets `is_active=false` and returns `204` with no body.
- Repeated deactivation of the same own-tenant resource is idempotent and returns `204` again. Deactivation lookup logic must therefore include already-inactive records while remaining tenant-scoped.
- Reactivation, if permitted, occurs only through an explicitly documented update field and permission rule.
- Bookings have no `DELETE` endpoint, per the accepted Decision Log entry dated 2026-08-16. Cancellation is a permitted status transition defined by the booking contract's state machine.
- Illegal status transitions return `409 illegal_status_transition`.
- Mutations that create activity/audit records must commit the domain change and its required audit record atomically.

## 10. Booking Concurrency and Time Rules

- Booking `end_time` is derived by the server from `start_time + service.duration_minutes`; clients cannot override it.
- Bookings use half-open intervals: `[start_time, end_time)`. Two bookings overlap exactly when `existing.start_time < candidate.end_time` and `existing.end_time > candidate.start_time`. Therefore, a booking ending at `10:00` does not conflict with one starting at `10:00`.
- Availability checks convert booking timestamps from UTC to the business timezone before comparing them with weekly staff availability windows.
- Availability containment uses `window.start_time <= booking.start_time` and `booking.end_time <= window.end_time`. A booking may end exactly when the availability window ends.
- A staff member with no availability rows is not bookable and produces `409 staff_not_bookable`.
- A booking outside the applicable availability window produces `409 outside_availability`.
- Booking overlap detection must be transaction-safe. A non-atomic “check, then insert/update” sequence is insufficient because concurrent requests could both pass the check.
- The booking implementation must use a documented PostgreSQL-safe strategy—such as an applicable exclusion constraint or transaction/locking strategy—and translate the resulting conflict consistently to `409 booking_conflict`.
- Cancelled bookings do not block future time unless the booking contract explicitly states otherwise. The booking contract defines which statuses participate in overlap detection.
- Weekly availability windows cannot cross midnight because the schema requires `start_time < end_time`. Overnight availability is represented as two windows on adjacent weekdays.
- Availability `weekday` uses `0 = Monday` through `6 = Sunday`, matching Python's `date.weekday()`. The authoritative DBML source must contain the same note; the PDF export is not sufficient documentation of this convention.

## 11. Response Consistency

- Resource responses include `id`. They include `created_at` and `updated_at` only where those fields exist in the authoritative schema.
- Enum values are the exact database enum strings, for example `in_progress`, `no_show`, and `partially_refunded`.
- Monetary amounts are serialized as fixed-scale decimal strings, for example `"45.00"`, never as JSON floating-point numbers and never with currency symbols.
- Every monetary amount is accompanied by an ISO 4217 `currency` field.
- Service responses derive `currency` from the authenticated business's current `businesses.currency`, because `services` stores `price` but does not store a separate currency.
- Payment responses use the payment record's stored currency so historical payments remain unchanged if the business default currency later changes.
- Nullable response fields are returned explicitly as `null` unless an individual contract documents a sparse response.
- Embedded resources follow the same authoritative-schema rule. For example, staff responses that embed availability rows must not invent `created_at` or `updated_at` fields that do not exist on `staff_availability`.
- Empty collections return `"data": []` with valid pagination metadata, never `404`.
- A `204` response contains no JSON body.

## 12. Contract Completion Checklist

Before an endpoint contract is approved, confirm that it defines:

- authentication and allowed roles;
- request path, query, and body schemas;
- response schema and examples;
- tenant-scoping behavior;
- tenant-scoped request-body relationship validation and its inherited `404 not_found` behavior;
- active/inactive-resource behavior;
- validation, normalization, and writable/read-only fields;
- filters, search fields, sorting, pagination, and null ordering where applicable;
- success and error status codes using the shared registry;
- business-rule and state-transition behavior;
- audit-log behavior;
- concurrency/transaction behavior where competing writes are possible; and
- automated tests, including authorization and cross-tenant cases.

---

*FINAL — Revision 3. Verified through the complete Authentication, Customers, Staff, Services, and Bookings contract set on 2026-08-16. Revision 3 registers `inactive_resource`; the request-body relationship-reference `404` rule is also pinned explicitly in §3.*
