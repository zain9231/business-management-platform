# Staff API Contract — Business Management Platform

**Phase 0 artifact.** Endpoint contract for `GET /staff`, `POST /staff`, `GET /staff/{id}`, `PUT /staff/{id}`, `DELETE /staff/{id}`, `GET /staff/{id}/availability`, and `PUT /staff/{id}/availability`. Written against the Shared API Conventions (FINAL — Revision 3, 2026-08-16), the Authentication API Contract (FINAL, 2026-08-16), the Customers API Contract (FINAL — Revision 2), Specification v1.2 (Sections 5.3, 8.4, 8.9, 19, 40–42, 44, 54, and 55.1), and the authoritative DBML ERD. Status: **FINAL — Revision 2**, verified against those artifacts on 2026-08-16.

**Revision 2 verification markers:** the two post-freeze clarifications in §2.1 and §2.2 are accepted in the Specification Decision Log; §2.2 and §9 define the `24:00:00` day-end boundary now recorded in the authoritative DBML; request-body relationship references inherit Conventions §3's `404` rule; §9.2 states the audit no-op asymmetry; and §10 carries the colleague-name dependency into the bookings contract.

All endpoints live under `/api/v1`, are protected, and inherit the protected-endpoint authentication behavior defined in Auth Contract §4 (`authentication_required`, `invalid_token`, `token_expired`, `403 inactive_account`) without restating it. All errors use the shared envelope and registry. Tenant scoping follows Conventions §3: every lookup, relationship validation, count, and mutation is scoped to the authenticated user's `business_id`; cross-tenant resources return `404 not_found`.

---

## 1. Resource Representations

### 1.1 Staff summary

`GET /staff` returns summary objects so a page of staff does not multiply into an unbounded availability payload:

```json
{
  "id": "4c5b5d54-392f-4d2a-93ef-1234567890ab",
  "user_id": "8f14e45f-ea5e-4b8b-9a0b-1234567890ab",
  "name": "Amina Shah",
  "email": "amina@example.test",
  "phone": "+92 300 7654321",
  "position": "Senior Stylist",
  "specialization": "Colour and bridal styling",
  "is_active": true,
  "created_at": "2026-08-16T10:00:00Z",
  "updated_at": "2026-08-16T10:00:00Z"
}
```

### 1.2 Staff detail

Single-resource reads and successful staff creates/updates return the summary fields plus embedded availability:

```json
{
  "id": "4c5b5d54-392f-4d2a-93ef-1234567890ab",
  "user_id": "8f14e45f-ea5e-4b8b-9a0b-1234567890ab",
  "name": "Amina Shah",
  "email": "amina@example.test",
  "phone": "+92 300 7654321",
  "position": "Senior Stylist",
  "specialization": "Colour and bridal styling",
  "is_active": true,
  "created_at": "2026-08-16T10:00:00Z",
  "updated_at": "2026-08-16T10:00:00Z",
  "availability": {
    "timezone": "Asia/Karachi",
    "windows": [
      {
        "id": "990e8400-e29b-41d4-a716-1234567890ab",
        "weekday": 0,
        "start_time": "09:00:00",
        "end_time": "17:00:00"
      }
    ]
  }
}
```

- `business_id` is never serialized. It is derived from the authenticated tenant.
- Nullable staff fields (`user_id`, `email`, `phone`, `position`, `specialization`) are returned explicitly as `null` when unset.
- `availability.timezone` is the authenticated business's current IANA timezone and is server-derived context, not a `staff_availability` column.
- Availability rows include `id`, `weekday`, `start_time`, and `end_time`. They do **not** invent `created_at` or `updated_at`, which do not exist in the authoritative DBML.
- Availability rows are ordered by `weekday ASC, start_time ASC, end_time ASC, id ASC`.

### 1.3 Staff field rules

| Field | Type | Writable | Rules |
|---|---|---|---|
| `id` | UUID | no | Server-generated |
| `user_id` | UUID \| null | yes | Optional link to a user in the same tenant; see §2.3 |
| `name` | string | yes | **Required.** Trimmed; 1–200 chars after trimming |
| `email` | string \| null | yes | Optional. Trimmed, lowercased; valid email syntax; max 320 chars; not unique |
| `phone` | string \| null | yes | Optional. Trimmed; max 50 chars; no format validation in the MVP |
| `position` | string \| null | yes | Optional. Trimmed; max 150 chars |
| `specialization` | string \| null | yes | Optional. Trimmed; max 200 chars |
| `is_active` | boolean | conditionally | Writable via staff `PUT` by Administrator/Manager; defaults to `true` on create and is not accepted on `POST` |
| `created_at` / `updated_at` | timestamp | no | Server-managed staff-row timestamps |
| `availability` | object | no on staff writes | Managed only through `/staff/{id}/availability`; rejected in staff `POST`/`PUT` |

Read-only fields supplied in a write return `422 validation_error`. Empty-string values for optional text fields are normalized to `null` after trimming. Staff email lowercasing is a contact/search normalization rule, not an authentication or uniqueness rule; it improves consistent display and manual duplicate review.

---

## 2. Contract-Level Decisions

### 2.1 Staff visibility and self-service availability

The frozen permission matrix gives Staff a “relevant subset” of staff visibility and availability management “where permitted,” but the MVP has no granular permission configuration. The accepted post-freeze Decision Log clarification fixes the rule as follows:

| Action | Administrator | Manager | Staff |
|---|---|---|---|
| List/view staff | Full tenant | Full tenant | Only rows whose `user_id` equals the authenticated user's id |
| Create/edit/deactivate/reactivate staff | Yes | Yes | No — `403 permission_denied` |
| View availability | Any own-tenant staff row | Any own-tenant staff row | Only linked staff rows |
| Replace availability | Any own-tenant staff row | Any own-tenant staff row | Only linked staff rows |

The Staff subset is authorization-scoped: a Staff caller requesting an unlinked own-tenant staff id receives `404 not_found`, the same response as a nonexistent or cross-tenant id. Lists apply the link predicate before counts and pagination. A Staff user with no linked staff rows receives an empty list and cannot access any staff detail or availability resource.

Rationale: `staff.user_id` is the only authoritative relationship between a login principal and an operational staff resource. Granting availability replacement only across that link gives the user story practical MVP behavior without exposing unrelated staff data or inventing Phase 8 configuration. Administrator/Manager control the link and can revoke self-service access by unlinking the row.

**Accepted Decision Log clarification:** for the MVP, a Staff user's relevant staff subset is every own-tenant staff row linked through `staff.user_id = authenticated_user.id`. Staff may view those rows and replace their availability, but cannot create, edit, activate, or deactivate staff records. Configurable availability permissions and broader subset rules are deferred.

### 2.2 Availability is a whole-collection subresource

The initial endpoint inventory lists staff CRUD but the specification also requires availability management. The MVP adds:

- `GET /staff/{id}/availability`
- `PUT /staff/{id}/availability`

`PUT` replaces the complete bounded weekly schedule. There are no per-window `POST`, `PUT`, or `DELETE` endpoints. This avoids ordering-dependent partial edits, gives one atomic scheduling change, and makes `[]` the explicit operation for clearing availability.

**Accepted Decision Log clarification:** add GET/PUT `/staff/{id}/availability` to the Phase 0 Staff contract. Availability is managed as an atomic whole-collection replacement; per-window mutation endpoints are not part of the MVP. Same-weekday overlapping or touching windows are coalesced on write, and `24:00:00` is the legal exact day-end value for splitting overnight availability. The authoritative DBML records the same `end_time` value-domain rule.

### 2.3 `user_id` is an operational link, not a role assignment

Administrator and Manager may link or unlink an own-tenant user through `user_id`. This does not create a user, change a user's role, or grant access beyond the rules in §2.1. Per Conventions §3, a nonexistent or cross-tenant `user_id` supplied in the body returns `404 not_found` without revealing which case occurred; a malformed UUID remains `422 validation_error`. The bookings contract inherits the same `404` rule for body references such as `customer_id`, `staff_id`, and `service_id`. The linked user may be inactive or may hold any fixed role; user/account lifecycle remains owned by the future users contract.

The authoritative DBML does not make `(business_id, user_id)` unique. This contract therefore does not invent uniqueness: one user may be linked to multiple staff rows, and a Staff principal's relevant subset includes all of them. If the product later requires one user ↔ one staff row, both the DBML and this contract must be revised with a concurrency-safe uniqueness constraint; application-only duplicate checking is insufficient.

### 2.4 Staff contact fields are not unique

Staff `email` and `phone` are operational contact data, not credentials. No staff field is unique under the authoritative schema, so `duplicate_value` is never returned by this contract. Login identity and global email uniqueness belong to `users.email`.

### 2.5 Deactivation preserves history and availability

`DELETE` soft-deactivates the staff row. It does not delete availability or modify existing bookings. Preserving the weekly schedule makes reactivation reversible. Direct staff and availability reads may return inactive staff. Reactivation is staff `PUT` with `"is_active": true` by Administrator/Manager.

Whether an inactive staff member may receive a new or rescheduled booking belongs to the bookings contract; expected behavior is `409 staff_not_bookable`. The bookings contract must make that validation transaction-safe relative to concurrent staff deactivation or reactivation.

### 2.6 Activity-record ownership and atomicity

Every staff activity record uses `business_id = authenticated_user.business_id`, `user_id = authenticated_user.id`, `entity_type = "staff"`, and `entity_id = staff.id`. The domain mutation and required activity record commit or roll back together.

---

## 3. `GET /staff`

**Roles:** Administrator, Manager, Staff, subject to §2.1.

### Query parameters

| Parameter | Behavior |
|---|---|
| `page`, `page_size` | Shared pagination (Conventions §6) |
| `search` | Case-insensitive literal substring match against `name`, `email`, `phone`, `position`, and `specialization`. Trimmed; max 200 chars; empty after trimming = omitted. SQL `%`, `_`, and the configured escape character are escaped |
| `is_active` | `true`/`false`; defaults to `true` |
| `sort` | Whitelist: `name`, `created_at`. Default: `name` ascending. The server appends `id ASC` for every permitted sort |

Unknown, repeated where disallowed, or malformed parameters return `422 validation_error`. Neither sortable field is nullable, so null ordering is not applicable. Phone search matches the stored string as-is; no normalized-phone search is promised.

### Success — `200 OK`

Shared pagination envelope; `data` contains §1.1 summaries. Availability is deliberately omitted from list items. Empty results return `data: []`, never `404`.

---

## 4. `POST /staff`

**Roles:** Administrator, Manager.

### Request body

```json
{
  "user_id": null,
  "name": "Amina Shah",
  "email": "Amina@Example.test",
  "phone": "+92 300 7654321",
  "position": "Senior Stylist",
  "specialization": "Colour and bridal styling"
}
```

Only `name` is required. Optional fields may be omitted or sent as `null`. `is_active`, `availability`, and read-only or unknown fields return `422 validation_error`.

### Behavior

Validate and normalize → validate `user_id` within the authenticated tenant when non-null → insert with principal-derived `business_id` → write `staff.create` activity atomically → return the persisted §1.2 detail with an empty availability schedule.

### Success — `201 Created`

Full §1.2 detail; `Location: /api/v1/staff/{id}`.

### Errors

| Case | Response |
|---|---|
| Validation failure or forbidden field | `422 validation_error` |
| Staff role | `403 permission_denied` |
| Nonexistent or cross-tenant `user_id` | `404 not_found` |

---

## 5. `GET /staff/{id}`

**Roles:** Administrator, Manager, Staff, subject to §2.1.

Returns the §1.2 detail. Inactive staff are returned when otherwise visible. Malformed UUID → `422 validation_error`; nonexistent, cross-tenant, or Staff-invisible id → `404 not_found`.

---

## 6. `PUT /staff/{id}`

**Roles:** Administrator, Manager.

Complete replacement of all client-writable staff fields: `user_id`, `name`, `email`, `phone`, `position`, `specialization`, and `is_active`. All seven must be present; omission returns `422 validation_error`. `availability` is not a staff-write field and is rejected.

### Behavior

Validate and normalize → validate non-null `user_id` within the tenant → lock or guard the tenant-scoped staff row → update → write one activity record atomically → return §1.2 detail. Updating an inactive staff row is permitted.

- Use `staff.reactivate` or `staff.deactivate` when `is_active` changes.
- A mixed PUT that changes `is_active` and other fields writes **exactly one** transition activity record and no additional `staff.update` record.
- If `is_active` does not change, use `staff.update`, including for a no-op replacement.

`updated_at` is refreshed by a successful staff-row PUT. It is not refreshed by availability-only changes because those mutate child rows, not the staff row.

### Success — `200 OK`

Full updated §1.2 detail.

### Errors

| Case | Response |
|---|---|
| Missing writable field, invalid value, read-only/unknown field | `422 validation_error` |
| Staff role | `403 permission_denied` |
| Nonexistent or cross-tenant staff id or `user_id` | `404 not_found` |

---

## 7. `DELETE /staff/{id}`

**Roles:** Administrator, Manager.

Soft deletion per §2.5. Set `is_active = false`; write `staff.deactivate` atomically only when the state changes. Repeated and concurrent deletes return `204` but produce exactly one deactivation activity record.

The implementation uses a guarded tenant-scoped update or row lock. If no active row is changed, an inactive-inclusive tenant-scoped existence check distinguishes an already-inactive row (`204`) from a nonexistent or cross-tenant id (`404`). Availability and bookings are not deleted.

### Success — `204 No Content`

No response body.

### Errors

| Case | Response |
|---|---|
| Staff role | `403 permission_denied` |
| Nonexistent or cross-tenant id | `404 not_found` |
| Malformed UUID | `422 validation_error` |

---

## 8. `GET /staff/{id}/availability`

**Roles:** Administrator, Manager, Staff, subject to §2.1.

### Success — `200 OK`

```json
{
  "staff_id": "4c5b5d54-392f-4d2a-93ef-1234567890ab",
  "timezone": "Asia/Karachi",
  "windows": [
    {
      "id": "990e8400-e29b-41d4-a716-1234567890ab",
      "weekday": 0,
      "start_time": "09:00:00",
      "end_time": "17:00:00"
    }
  ]
}
```

This child collection is unpaginated because §9 caps the stored schedule at 100 canonical windows per staff row. An inactive but otherwise visible staff row returns its schedule. No windows returns `"windows": []`.

Malformed UUID → `422 validation_error`; nonexistent, cross-tenant, or Staff-invisible id → `404 not_found`.

---

## 9. `PUT /staff/{id}/availability`

**Roles:** Administrator, Manager; Staff only for a linked row under §2.1.

### Request body

```json
{
  "windows": [
    {
      "weekday": 0,
      "start_time": "09:00:00",
      "end_time": "12:00:00"
    },
    {
      "weekday": 0,
      "start_time": "12:00:00",
      "end_time": "17:00:00"
    }
  ]
}
```

`windows` is required and contains 0–100 input rows. Window ids and any other fields are rejected. `[]` clears the complete schedule and makes the staff member unbookable until availability is configured again.

### 9.1 Window validation

| Field | Rules |
|---|---|
| `weekday` | Integer `0`–`6`; `0 = Monday`, `6 = Sunday`; booleans are not accepted as integers |
| `start_time` | Business-local wall-clock `HH:MM:SS`; `00:00:00` through `23:59:59`; no offset or fractional seconds |
| `end_time` | Business-local wall-clock `HH:MM:SS`; `00:00:01` through `24:00:00`; `24:00:00` is allowed only as the exact day-end boundary; no offset or fractional seconds |
| ordering | `start_time < end_time`; zero-length and backward/cross-midnight rows are rejected |

`24:00:00` permits an exact split for overnight availability: for example, Monday `22:00:00–24:00:00` plus Tuesday `00:00:00–02:00:00`. A single row may not cross midnight.

Implementation note: PostgreSQL can store the exact `24:00:00` boundary, but Python's standard `datetime.time` cannot represent it and common PostgreSQL drivers may reject it on load. The persistence layer must therefore handle availability times as validated strings/custom values (for example, selecting the columns as text) or register an explicit adapter; it must not silently normalize `24:00:00` to `00:00:00` on the same weekday. Test 12 is the shipping guard for this boundary.

### 9.2 Canonicalization and replacement

After validation, the server canonicalizes the request before persistence:

1. Group by weekday and sort by `start_time`, then `end_time`.
2. Merge same-weekday windows that overlap or touch. If the next `start_time <= current end_time`, replace them with their union. Exact duplicates are absorbed. Example: `09:00–12:00`, `11:00–14:00`, and `14:00–17:00` become one `09:00–17:00` row.
3. Compare the canonical `(weekday, start_time, end_time)` set with the stored set, ignoring row ids and order.
4. If identical, return the existing rows unchanged and write no activity record.
5. If different, atomically replace all availability rows and write exactly one `staff.availability.update` activity record.

Unlike a staff-row no-op `PUT`, which writes `staff.update` under §6, a canonically identical availability replacement is not audited because no stored availability state changed. This asymmetry is deliberate.

Canonicalization never merges across different weekdays. Continuous booking-time availability across midnight (including `24:00:00` → next-day `00:00:00`) is evaluated by the bookings contract after UTC timestamps are converted to the business timezone.

Changed replacements generate new availability-row ids; clients must treat those ids as opaque response identifiers and must not use them for mutation. Output is the canonical sorted schedule in the §8 response shape.

### 9.3 Concurrency and authorization race handling

The replacement transaction locks the tenant-scoped staff row before rechecking authorization and comparing/replacing availability. For a Staff caller, the locked row must still have `user_id = authenticated_user.id`; if an Administrator/Manager unlinked it while the request waited, the Staff request returns `404` and makes no change. Staff deactivation does not itself revoke linked availability self-service; unlinking the row does.

Competing valid replacements are serialized by the staff-row lock; the later lock holder's complete representation wins. The MVP has no ETag/version precondition. Delete/insert operations and the activity record commit or roll back together.

### Success — `200 OK`

The §8 response shape with the canonical persisted schedule.

### Errors

| Case | Response |
|---|---|
| Missing `windows`, invalid weekday/time/order, more than 100 input rows, row id, or unknown field | `422 validation_error` with indexed field paths |
| Staff caller for an unlinked row | `404 not_found` |
| Nonexistent or cross-tenant staff id | `404 not_found` |

---

## 10. Interaction With Bookings and Business Settings

- A staff member with no availability rows is not bookable (`409 staff_not_bookable`), per the accepted empty-availability decision.
- Booking timestamps are stored in UTC and evaluated against weekly windows in the business timezone. DST ambiguity/nonexistence, cross-midnight continuity, runtime containment, booking overlap, and locking against concurrent bookings belong to the bookings contract.
- Deactivating staff does not cancel, reschedule, or otherwise mutate historical/future bookings. Creation or rescheduling against inactive staff is expected to fail with `409 staff_not_bookable`; the booking contract owns the final rule and race-safe implementation.
- Same-day overlap/touch coalescing is owned by this contract at write time. The bookings contract may rely on canonical stored rows but must still define how a booking interval is mapped across local dates/weekdays.
- Staff visibility creates a response dependency for bookings: if a Staff caller can ever see a booking assigned to an unlinked colleague, the booking response must include the colleague's minimum display identity (at least staff id and name) or a future authorization revision must broaden staff visibility. The frontend must not be expected to resolve that colleague through `GET /staff/{id}`, which correctly returns `404` under §2.1. The bookings contract must confirm either self-only Staff booking visibility or the embedded-identity alternative explicitly.
- The MVP has no business operating-hours table and no one-off availability exceptions. Staff weekly windows are the sole stored availability source.
- A later business-timezone change does not rewrite wall-clock availability rows. The business-settings contract must define confirmation, audit, and user-warning behavior for that change.

---

## 11. Required Automated Tests

1. Create with all fields and only `name`; correct normalization, `201`, `Location`, empty availability, and atomic `staff.create` activity.
2. Field validation: missing/blank/oversized name; invalid/oversized email; oversized phone/position/specialization; `is_active` or `availability` on POST; read-only/unknown fields → `422` with correct field paths.
3. Contact normalization: email trimmed/lowercased, optional empty strings → `null`; duplicate staff emails and duplicate `user_id` links are accepted because the DBML defines no uniqueness.
4. Relationship scoping: valid own-tenant `user_id` succeeds; nonexistent and cross-tenant `user_id` each return indistinguishable `404` responses.
5. Administrator/Manager list, detail, create, PUT, DELETE, and availability operations succeed within tenant; Staff scalar POST/PUT/DELETE return `403 permission_denied`.
6. Staff subset: a Staff user sees all and only rows linked to their user id; counts/pagination are subset-scoped; unlinked detail/availability ids return the same `404` as nonexistent/cross-tenant ids; no links yields an empty list.
7. List default excludes inactive staff; `is_active=false` returns inactive; direct detail and availability GET return an inactive visible row.
8. Search independently matches name, email, phone, position, and specialization; case-insensitive literal handling escapes `%`, `_`, and the configured escape character; search composes with active filter and Staff subset.
9. Sort by `name`, `-name`, `created_at`, and `-created_at`; unsupported/multi-field sorts return `422`; duplicate values use `id ASC` tie-breaker.
10. PUT requires all seven writable fields; reactivation succeeds; a mixed PUT changing `is_active` and other fields writes one transition activity and no `staff.update`; a non-transition PUT writes one `staff.update`.
11. Sequential and concurrent DELETE calls all return `204` for an existing own-tenant row while exactly one `staff.deactivate` activity exists; availability and bookings remain.
12. Availability validation: weekday boundaries; boolean weekday rejection; strict seconds; `24:00:00` allowed only for end; invalid `24:00:01`; zero/backward/cross-midnight row; unknown/read-only fields; 101 input rows — correct `422` field paths.
13. Availability canonicalization: unordered, duplicate, overlapping, and touching same-day windows persist as the minimal sorted union; separate non-touching and different-weekday windows remain separate.
14. Availability replacement: initial write; changed full replacement; `[]` clear; exact canonical no-op preserves ids and writes no activity; changed replacement writes exactly one `staff.availability.update`; insertion/audit failure rolls back the whole replacement.
15. Availability concurrency: two replacements serialize and the later lock holder wins completely; Staff self-service rechecks the link after locking; concurrent unlink causes the waiting Staff write to return `404` without mutation.
16. Cross-tenant staff ids never appear in lists/counts and return indistinguishable `404` for detail, PUT, DELETE, and both availability endpoints.
17. Protected-route wiring: missing, invalid, expired, and inactive-account credentials produce the inherited Auth Contract §4 errors on every endpoint.
18. Strict query validation, page-beyond-results behavior, summary/detail response shapes, explicit nullable fields, and absence of fabricated availability timestamps match the shared conventions.

---

*FINAL — Revision 2. Verified against the Shared API Conventions, Authentication API Contract, Customers API Contract, Specification v1.2 Decision Log, and authoritative DBML on 2026-08-16. Next: services, then bookings (state machine, local-time availability evaluation, cross-midnight continuity, colleague identity, and concurrency).*
