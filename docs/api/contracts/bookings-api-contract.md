# Bookings API Contract — Business Management Platform

**Phase 0 artifact.** Endpoint contract for `GET /bookings`, `POST /bookings`, `GET /bookings/{id}`, and `PUT /bookings/{id}`. `DELETE /bookings/{id}` does not exist. Written against the Shared API Conventions (FINAL — Revision 3, 2026-08-16), Authentication API Contract (FINAL), Customers API Contract (FINAL — Revision 2), Staff API Contract (FINAL — Revision 2), Services API Contract (FINAL), Specification v1.2 (Sections 5, 8.7, 9, 18, 19, 40–42, 44, and 54), its accepted Decision Log, and the authoritative DBML ERD. Status: **FINAL — Revision 2**, verified against those artifacts on 2026-08-16.

This contract is the Specification-delegated single source of truth for the booking state machine, permitted roles, scheduling validation, and overlap behavior. All endpoints live under `/api/v1`, are protected, use the shared error envelope/registry, and derive tenant context exclusively from the authenticated principal. Every lookup, body reference, filter, count, lock, and mutation is tenant-scoped.

---

## 1. Resource Representation

```json
{
  "id": "75f516d7-73f4-4557-9fb4-2a8b76efc793",
  "customer_id": "d3b07384-d9a0-4c1a-8f3e-1234567890ab",
  "staff_id": "4c5b5d54-392f-4d2a-93ef-1234567890ab",
  "service_id": "8be30a73-5859-49cd-bac8-f6b26b1058bf",
  "start_time": "2026-08-20T09:00:00Z",
  "end_time": "2026-08-20T09:45:00Z",
  "status": "scheduled",
  "notes": "First appointment.",
  "custom_fields": {},
  "created_at": "2026-08-16T10:00:00Z",
  "updated_at": "2026-08-16T10:00:00Z"
}
```

- `business_id` is never serialized or accepted.
- The six exact status values are `scheduled`, `confirmed`, `in_progress`, `completed`, `cancelled`, and `no_show`.
- `end_time` is read-only and is calculated as the UTC `start_time` instant plus the selected service's `duration_minutes` in elapsed minutes. It is not wall-clock addition.
- `notes` is explicitly `null` when unset.
- `custom_fields` is returned as stored, `{}` by default, but is read-only until Phase 8.
- The response intentionally contains schema-backed ids rather than embedded customer/staff/service objects. The Staff visibility rule in §2.1 ensures a Staff caller never needs to resolve an unlinked colleague.

### 1.1 Field rules

| Field | Type | Writable | Rules |
|---|---|---|---|
| `id` | UUID | no | Server-generated |
| `customer_id` | UUID | yes | Required; existing own-tenant customer; active for creation or reassignment |
| `staff_id` | UUID | yes | Required; existing own-tenant staff row; active and bookable for creation or scheduling changes |
| `service_id` | UUID | yes | Required; existing own-tenant service; active for creation or service change |
| `start_time` | timestamp | yes | Required; explicit UTC offset; normalized to UTC; creation/reschedule may not target an instant earlier than the transaction timestamp |
| `end_time` | timestamp | no | Server-derived from locked service duration; rejected in writes |
| `status` | enum | conditionally | Defaults to `scheduled` on create and is rejected on `POST`; writable on `PUT` only through §3's legal transitions |
| `notes` | string \| null | yes | Optional; trimmed; empty becomes `null`; max 5,000 characters |
| `custom_fields` | object | no (MVP) | Rejected in writes until Phase 8 |
| `created_at` / `updated_at` | timestamp | no | Server-managed |

Malformed UUIDs/timestamps, naive timestamps, unknown fields, read-only fields, and invalid enum values return `422 validation_error`. A nonexistent or cross-tenant body reference returns indistinguishable `404 not_found` under Conventions §3. Existing-but-inactive references are separate business-state conflicts under §4.2.

The past-start rule is deliberately a field-level request constraint and therefore returns `422 validation_error`, not `409`: creation/rescheduling representations must target a current or future instant before business-state conflict checks run.

---

## 2. Authorization and Visibility

### 2.1 MVP role scope

| Action | Administrator | Manager | Staff |
|---|---|---|---|
| List/view bookings | All own-tenant | All own-tenant | Only bookings whose `staff_id` is linked by `staff.user_id = authenticated_user.id` |
| Create | Any valid own-tenant staff row | Any valid own-tenant staff row | Only for a linked staff row |
| Reschedule/reassign customer, staff, or service | Yes | Yes | No |
| Edit notes | Yes | Yes | Yes, on a visible booking |
| Update status | All legal transitions | All legal transitions | Only the assigned-Staff transitions in §3.2, on a visible booking |
| Cancel | Yes | Yes | No |
| Delete | No endpoint | No endpoint | No endpoint |

The Staff subset uses the same authoritative link as the Staff contract. A Staff principal linked to multiple staff rows sees bookings for all of them; no links yields an empty collection. Direct access to an unlinked own-tenant booking returns the same `404 not_found` as nonexistent/cross-tenant. List predicates are applied before counts and pagination.

A Staff `POST` with an unlinked own-tenant `staff_id` returns `404`, not `403`, so the body cannot be used to enumerate hidden colleague rows. A Staff `PUT` must repeat the stored `customer_id`, `staff_id`, `service_id`, and `start_time` unchanged; attempting to change any returns `403 permission_denied`.

This resolves the frozen matrix's “within permission scope” and “configuration-dependent” Staff cells without inventing Phase 8 configuration: Staff operate only their linked bookings, may create them and update their status/notes, and cannot reschedule, reassign, or cancel them. **The Specification Decision Log records this as an accepted post-freeze clarification.**

**Accepted Decision Log clarification:** in the MVP, Staff booking visibility and mutation scope is limited to bookings assigned to staff rows linked through `staff.user_id = authenticated_user.id`. Staff may create bookings for those rows and update their notes or assigned-Staff status transitions, but may not reassign, reschedule, or cancel bookings; configurable expansion is deferred to Phase 8.

### 2.2 Colleague identity dependency resolved as self-only

Staff never receive bookings assigned to unlinked colleagues. The booking response therefore does not need to embed a colleague name, and the frontend can resolve the visible `staff_id` through the Staff contract. If shared-team calendar visibility is added later, the booking response must embed the colleague's minimum display identity or staff visibility must be expanded through an authorization revision.

### 2.3 No deletion

Bookings are historical records. Cancellation is a state transition; there is no hard- or soft-delete operation. An authenticated `DELETE /api/v1/bookings/{id}` returns `405 method_not_allowed` with the shared envelope and no mutation/audit record.

### 2.4 `custom_fields` frozen until Phase 8

The JSONB column is returned but not writable. Any `custom_fields` key in `POST` or `PUT` returns `422 validation_error`. Phase 8 must explicitly amend this rule after per-business definitions exist.

---

## 3. Booking State Machine

### 3.1 States and blocking participation

| Status | Meaning | Terminal | Blocks overlapping bookings |
|---|---|---:|---:|
| `scheduled` | Created, not yet confirmed | no | yes |
| `confirmed` | Appointment acknowledged | no | yes |
| `in_progress` | Service has started | no | yes |
| `completed` | Service finished | yes | no |
| `cancelled` | Appointment cancelled | yes | no |
| `no_show` | Customer did not attend | yes | no |

Only `scheduled`, `confirmed`, and `in_progress` participate in overlap detection. `cancelled` and `no_show` never block a replacement slot. `completed` is also nonblocking; new/rescheduled bookings cannot begin in the past, so historical completed intervals do not create operational conflicts.

Terminal states cannot be reopened or changed to another status in the MVP. Their notes may still be corrected by an authorized caller through a PUT that repeats all immutable fields and the same status.

### 3.2 Legal transitions and roles

All temporal guards use one database transaction timestamp.

| From | To | Administrator / Manager | Assigned Staff | Temporal guard | Audit action |
|---|---|---:|---:|---|---|
| `scheduled` | `confirmed` | yes | yes | transaction time `< end_time` | `booking.confirm` |
| `scheduled` | `in_progress` | yes | yes | `start_time <=` transaction time `< end_time` | `booking.start` |
| `scheduled` | `cancelled` | yes | no | none | `booking.cancel` |
| `scheduled` | `no_show` | yes | yes | transaction time `>= start_time` | `booking.no_show` |
| `confirmed` | `in_progress` | yes | yes | `start_time <=` transaction time `< end_time` | `booking.start` |
| `confirmed` | `cancelled` | yes | no | none | `booking.cancel` |
| `confirmed` | `no_show` | yes | yes | transaction time `>= start_time` | `booking.no_show` |
| `in_progress` | `completed` | yes | yes | transaction time `>= start_time` | `booking.complete` |
| `in_progress` | `cancelled` | yes | no | none | `booking.cancel` |

Every other status change returns `409 illegal_status_transition`, including a listed transition attempted before/after its temporal guard or by a terminal booking. A syntactically valid Staff attempt to perform an Administrator/Manager-only transition returns `403 permission_denied` rather than `409`, without changing the row.

The `no_show` guard intentionally begins at `start_time`, not `end_time`: the MVP has no configurable grace period, and operational staff must be able to release a missed slot once the appointment is due. A later configuration contract may add a grace period. The absence of a direct `scheduled → completed` shortcut is also deliberate; even walk-ins use `scheduled → in_progress → completed` so service start and completion remain separate, auditable actions.

A PUT may change status together with notes, but it may not change status together with `customer_id`, `staff_id`, `service_id`, or `start_time`. That mixed business action returns `422 validation_error` and must be performed as two PUTs so each schedule/reference change and state transition receives its own activity record. State and time are rechecked after locking the booking row so concurrent transitions cannot both succeed from the same prior state.

---

## 4. Scheduling Rules

### 4.1 Derived interval

For creation and every permitted scheduling change, the server locks/reads the selected service and calculates:

```text
end_time = start_time_utc + duration_minutes elapsed minutes
```

The client cannot override `end_time`. A later service-duration change does not recalculate an existing booking. The Services contract's 1–1,440-minute bound limits interval arithmetic.

### 4.2 Referenced-resource state

Creation and scheduling changes require all three references to exist in the tenant and be active:

| Condition | Response |
|---|---|
| Customer or service does not exist / is cross-tenant | `404 not_found` |
| Staff does not exist / is cross-tenant / is hidden from Staff caller | `404 not_found` |
| Customer or service exists but is inactive | `409 inactive_resource`, with the applicable body field |
| Staff exists but is inactive | `409 staff_not_bookable`, field `body.staff_id` |
| Active staff has no availability rows | `409 staff_not_bookable`, field `body.staff_id` |

Inactive customer/staff/service records remain valid on existing bookings. Notes and legal status transitions therefore do not re-run active-reference validation when the scheduling fields are unchanged. This permits an existing appointment to be cancelled, completed, or documented after a referenced resource is deactivated.

### 4.3 Availability evaluation in business-local time

Availability rows are recurring local-wall-time rules in the business's current IANA timezone; booking timestamps remain UTC instants. The implementation:

1. Calculates the UTC half-open booking interval `[start_time, end_time)`.
2. Materializes the relevant weekly availability windows for each business-local calendar date touched by that UTC interval. `end_time = 24:00:00` means `00:00:00` on the next local date, never same-day midnight.
3. Resolves a DST-ambiguous window start to the earlier occurrence and an ambiguous window end to the later occurrence. A boundary inside a nonexistent spring-forward gap advances to the first real local instant after the gap. A window that collapses to zero real duration contributes no availability.
4. Converts the dated windows to UTC half-open intervals, unions intervals that overlap or meet in real time, and requires the complete booking interval to be contained in one continuous union.

This real-instant materialization handles repeated/skipped wall times and permits cross-midnight continuity only when adjacent dated windows meet—for example Monday ending `24:00:00` and Tuesday beginning `00:00:00`. Canonicalization never merges weekdays in storage; continuity is evaluated here for the actual dates.

No availability rows returns `409 staff_not_bookable`. Rows exist but do not continuously contain the interval returns `409 outside_availability`. There is no business-hours table, holiday exception, buffer time, capacity override, or manual availability override in the MVP.

### 4.4 Half-open staff-overlap rule

An existing blocking booking conflicts exactly when:

```text
existing.start_time < candidate.end_time
AND existing.end_time > candidate.start_time
```

Therefore a booking ending at `10:00` does not conflict with one starting at `10:00`. Conflict checks are tenant- and staff-scoped and exclude the current booking during a reschedule. Customer and service overlaps are permitted; the MVP has one staff/resource per booking and no concurrent-capacity model.

### 4.5 PostgreSQL-safe serialization strategy

The MVP uses the staff row as the scheduling lock. The canonical global lock order for booking writes is: **booking row (PUT only) → customer row → staff row(s), ascending UUID when two are required → service row**.

1. `POST` has no booking row, so it locks customer → target staff → service with tenant predicates, then validates active state from the locked rows.
2. A scheduling/reference `PUT` locks the booking row → target customer → staff row(s) → target service. If `staff_id` changes, both the old and new staff rows are locked in ascending UUID order at the staff position in that sequence.
3. The target staff-row `FOR UPDATE` lock serializes all booking creates/reschedules for that staff member and coordinates with staff deactivation and availability replacement, which lock the same row.
4. While holding those locks, derive `end_time`, re-read availability, evaluate containment, query blocking overlaps, then insert/update the booking and activity record in one transaction.

A non-atomic check-then-write without the staff lock is forbidden. Every code path that creates or changes a booking interval must take the same lock; direct repository helpers may not bypass it. Lock acquisition order is fixed to prevent deadlocks. Conservative serialization across unrelated times for one staff member is an accepted MVP trade-off.

---

## 5. `GET /bookings`

**Roles:** all authenticated roles, visibility-scoped by §2.1.

### Query parameters

| Parameter | Behavior |
|---|---|
| `page`, `page_size` | Shared pagination |
| `start_time_from` | Offset-aware timestamp. Include bookings with `end_time > start_time_from` |
| `start_time_to` | Offset-aware timestamp. Include bookings with `start_time < start_time_to` |
| `staff_id` | Exact UUID filter |
| `customer_id` | Exact UUID filter |
| `service_id` | Exact UUID filter |
| `status` | One exact booking-status value |
| `sort` | Whitelist: `start_time`, `end_time`, `created_at`, `updated_at`, `status`; default `-start_time`; append `id ASC` |

When both time bounds are present, the query selects bookings overlapping the half-open calendar window `[start_time_from, start_time_to)`, not merely bookings that start inside it. `from >= to` returns `422 validation_error`. Either bound may be used independently. All timestamps are normalized to UTC.

Filters compose. For Staff, the linked-staff visibility predicate is applied before all filters, counts, and pagination. A filter referencing a valid but invisible or cross-tenant id simply produces no rows; filter endpoints do not disclose reference existence. None of the sortable fields is nullable, so null ordering is not applicable. Unknown/repeated/malformed parameters and unsupported/multi-field sorts return `422 validation_error`.

### Success — `200 OK`

Shared pagination envelope containing §1 representations. Empty results use `"data": []`.

---

## 6. `POST /bookings`

**Roles:** Administrator, Manager, Staff within §2.1.

### Request body

```json
{
  "customer_id": "d3b07384-d9a0-4c1a-8f3e-1234567890ab",
  "staff_id": "4c5b5d54-392f-4d2a-93ef-1234567890ab",
  "service_id": "8be30a73-5859-49cd-bac8-f6b26b1058bf",
  "start_time": "2026-08-20T14:00:00+05:00",
  "notes": null
}
```

All three ids and `start_time` are required. `notes` may be omitted or `null`. `status`, `end_time`, `custom_fields`, and all other read-only/unknown fields are rejected. Status defaults to `scheduled`.

### Behavior

Validate representation and role scope → execute §4's locked reference/active/availability/overlap checks → insert the derived interval and `scheduled` status → atomically write `booking.create` → return the persisted row. A required activity failure rolls back the booking.

### Success — `201 Created`

Full §1 representation; `Location: /api/v1/bookings/{id}`.

### Errors

| Case | Response |
|---|---|
| Invalid/missing field, past start, read-only/unknown field | `422 validation_error` |
| Staff attempts an unlinked assignment | `404 not_found` |
| Missing/cross-tenant body reference | `404 not_found` |
| Inactive customer/service | `409 inactive_resource` |
| Inactive/no-availability staff | `409 staff_not_bookable` |
| Interval not continuously available | `409 outside_availability` |
| Blocking overlap | `409 booking_conflict` |

---

## 7. `GET /bookings/{id}`

**Roles:** all authenticated roles, visibility-scoped by §2.1.

Returns §1 for every status, including historical terminal bookings and bookings whose referenced resources are now inactive. Malformed UUID returns `422 validation_error`. Nonexistent, cross-tenant, or Staff-invisible id returns indistinguishable `404 not_found`.

---

## 8. `PUT /bookings/{id}`

**Roles:** Administrator, Manager, and Staff within §2.1.

Complete replacement requires all client-writable fields: `customer_id`, `staff_id`, `service_id`, `start_time`, `status`, and `notes`. `notes` may be `null`; omission of any key returns `422 validation_error`.

### 8.1 Role and state restrictions

- Administrator/Manager may change scheduling fields only while the current status is `scheduled` or `confirmed`.
- `in_progress` and terminal bookings permit notes and legal status changes only; scheduling/reference fields must remain identical.
- Staff must always repeat all four scheduling/reference fields unchanged and may change only notes plus an assigned-Staff status transition from §3.2.
- A new/rescheduled `start_time` may not be earlier than the transaction timestamp.
- A PUT that changes `status` and any of `customer_id`, `staff_id`, `service_id`, or `start_time` is rejected with `422 validation_error`; callers submit two PUTs in the intended order.

A disallowed scheduling/reassignment attempt by Staff returns `403 permission_denied`. An Administrator/Manager scheduling change against an `in_progress` or terminal booking returns `409 illegal_status_transition` because the booking's state no longer permits rescheduling.

### 8.2 Validation, locking, and audit precedence

Lock the visible booking row and recheck authorization/state. If any scheduling/reference field changes, run the complete §4 locked pipeline and recompute `end_time`; otherwise preserve the stored interval and permit status/notes work even if a reference is now inactive.

Write exactly one activity record using these mutually exclusive cases:

1. If status changes (with notes optionally changing), use the transition action in §3.2.
2. Otherwise, if `staff_id`, `service_id`, or `start_time` changes, use `booking.reschedule`.
3. Otherwise use `booking.update`, including customer correction, notes-only change, or a full no-op PUT.

The booking update and activity record commit atomically. `updated_at` refreshes on every successful PUT.

### Success — `200 OK`

Full updated §1 representation.

### Errors

| Case | Response |
|---|---|
| Invalid/missing field, read-only/unknown field, or mixed status + reference/schedule change | `422 validation_error` |
| Staff scheduling/reassignment/cancellation attempt | `403 permission_denied` |
| Nonexistent/cross-tenant/Staff-invisible booking or body reference | `404 not_found` |
| Existing but inactive new customer/service reference | `409 inactive_resource` |
| Inactive/unavailable staff | `409 staff_not_bookable` or `409 outside_availability` as §4 defines |
| Blocking overlap | `409 booking_conflict` |
| Illegal/too-early/too-late transition or state-forbidden reschedule | `409 illegal_status_transition` |

---

## 9. Activity Records

Every activity row uses the authenticated tenant/user, `entity_type = "booking"`, and `entity_id = booking.id`. The complete action vocabulary is:

`booking.create` · `booking.update` · `booking.reschedule` · `booking.confirm` · `booking.start` · `booking.complete` · `booking.cancel` · `booking.no_show`

One successful mutation writes exactly one record. Failed validation, permission, state, availability, conflict, and no-method requests write none. Row changes and their activity record always commit or roll back together.

---

## 10. Required Automated Tests

1. Create a valid scheduled booking → derived elapsed-minute `end_time`, UTC normalization, `201`, `Location`, defaults, and atomic `booking.create`.
2. Strict input validation: missing ids/time, malformed/cross-type UUIDs, naive/invalid/past timestamp, oversized notes, status/end/custom/read-only/unknown POST fields, missing PUT fields → field-specific `422`.
3. Body-reference rules: nonexistent and cross-tenant customer/staff/service ids each return indistinguishable `404`; Staff unlinked own-tenant staff id also returns non-enumerating `404`.
4. Active-state rules: inactive customer/service → `409 inactive_resource`; inactive staff → `409 staff_not_bookable`; status/notes updates remain possible on existing bookings after any reference is deactivated.
5. Staff visibility: all and only bookings for every linked staff row; subset-scoped counts/pagination; unlinked direct ids return indistinguishable `404`; no links yields empty list.
6. Staff permissions: create for linked staff succeeds; reschedule/reassign/cancel returns `403`; allowed notes and assigned-Staff transitions succeed.
7. Administrator/Manager can create/reschedule/reassign and perform every legal transition; all roles receive `405 method_not_allowed` for authenticated DELETE with no mutation/audit.
8. Exhaustive state-machine table: every listed transition succeeds for each permitted role at valid times; `no_show` is permitted at/after `start_time`; every unlisted, terminal, too-early, and too-late transition returns `409 illegal_status_transition`; Staff-only prohibitions return `403`; `scheduled → completed` remains illegal.
9. Audit separation: a PUT mixing status with customer/staff/service/time changes returns `422` and writes nothing; the required two-call sequence writes one schedule/update record and one transition record; status + notes writes only the transition action; reschedule without status change writes only `booking.reschedule`; notes/customer/no-op PUT writes only `booking.update`.
10. Active-resource stability: duration, price, currency, contact data, and active-state changes after booking creation do not rewrite the stored booking interval or row.
11. Availability: no rows → `staff_not_bookable`; same-day containment boundaries; before/after window → `outside_availability`; adjacent non-touching gaps remain unavailable.
12. Cross-midnight continuity: `24:00:00` to next-day `00:00:00` permits continuous containment; any boundary gap rejects; a single stored row never crosses midnight.
13. DST spring-forward/fall-back tests in a real IANA zone cover nonexistent and ambiguous window boundaries, elapsed-time end calculation, materialized UTC unions, and full-day windows of 23/25 real hours.
14. Half-open conflicts: true overlap in each direction and exact duplicate reject; end-equals-start and start-equals-end adjacency succeeds.
15. Status participation: scheduled/confirmed/in-progress block; completed/cancelled/no-show do not; transitions to nonblocking states release the slot after commit.
16. Concurrent identical/overlapping POSTs for one staff member serialize: one succeeds and every conflicting loser receives `409 booking_conflict` with no partial row/audit.
17. Concurrent reschedules, create-vs-reschedule, reschedule between two staff rows, availability replacement, and staff deactivation follow fixed lock order without double-booking or deadlock.
18. Customer/service deactivation races serialize through locked reference rows: either booking commits first or the write observes inactive state; no booking is newly committed against an already-deactivated reference.
19. List filters independently and jointly cover overlap date range, staff, customer, service, and status; malformed values return `422`; Staff-invisible/cross-tenant filter ids return empty results without disclosure.
20. Sort every whitelisted field/direction; default `-start_time`; deterministic `id ASC`; unsupported/repeated/multi-sort returns `422`; page beyond results returns empty data/valid metadata.
21. Cross-tenant isolation for list, count, GET, PUT, references, availability, and overlap queries; responses do not reveal whether another-tenant data exists.
22. Protected-route wiring applies inherited missing/invalid/expired-token and inactive-account behavior on all routes.
23. Transaction rollback: booking insert/update and the required audit record roll back together; failures after locks release cleanly without orphan rows.

---

*FINAL — Revision 2. Verified against Shared API Conventions Revision 3, the finalized Authentication/Customers/Staff/Services contracts, the accepted Specification Decision Log, and the authoritative DBML on 2026-08-16. Phase 0's five API contracts are complete.*
