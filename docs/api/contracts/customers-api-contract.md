# Customers API Contract — Business Management Platform

**Phase 0 artifact.** Endpoint contract for `GET /customers`, `POST /customers`, `GET /customers/{id}`, `PUT /customers/{id}`, and `DELETE /customers/{id}`. Written against the Shared API Conventions (FINAL — Revision 3, 2026-08-16), the Authentication API Contract (FINAL, 2026-08-16), Specification v1.2 (Sections 5, 18, 19, 40, 41, 44, 54.2), and the authoritative DBML ERD. Status: **FINAL — Revision 2**, verified against those artifacts on 2026-08-16.

**Revision 2 verification markers:** Staff full-read is linked to the accepted Decision Log clarification in §2.1; customer-email lowercase normalization is justified in §2.2; mixed-field PUTs produce exactly one transition audit record in §6 and Test 9.

All endpoints live under `/api/v1`, are protected, and inherit the shared protected-endpoint authentication behavior defined in Auth Contract §4 (`authentication_required`, `invalid_token`, `token_expired`, `403 inactive_account`) without restating it. All list behavior follows the shared pagination, filtering, and sorting conventions. All errors use the shared envelope and registry. Tenant scoping follows Conventions §3: every query is scoped to the authenticated user's `business_id`; cross-tenant resources return `404 not_found`.

---

## 1. Resource Representation

```json
{
  "id": "d3b07384-d9a0-4c1a-8f3e-1234567890ab",
  "name": "Fatima Noor",
  "email": "fatima@example.test",
  "phone": "+92 300 1234567",
  "address": "House 12, Street 4, Wah Cantt",
  "notes": "Prefers afternoon appointments.",
  "is_active": true,
  "custom_fields": {},
  "created_at": "2026-08-16T10:00:00Z",
  "updated_at": "2026-08-16T10:00:00Z"
}
```

- `business_id` is **never** serialized on customer responses. It is implicit in the authenticated tenant, and omitting it removes any temptation for clients to key logic on it.
- Nullable fields (`email`, `phone`, `address`, `notes`) are returned explicitly as `null` when unset (Conventions §11).
- `custom_fields` is returned as its stored value, `{}` by default. See §2.4.

### 1.1 Field rules

| Field | Type | Writable | Rules |
|---|---|---|---|
| `id` | UUID | no | Server-generated |
| `name` | string | yes | **Required.** Trimmed; 1–200 chars after trimming |
| `email` | string \| null | yes | Optional. Trimmed, lowercased; valid email syntax; max 320 chars. **Not unique** — see §2.2 |
| `phone` | string \| null | yes | Optional. Trimmed; max 50 chars; **no format validation** in the MVP (international variety makes strict validation more harmful than helpful) |
| `address` | string \| null | yes | Optional. Trimmed; max 2,000 chars |
| `notes` | string \| null | yes | Optional. Trimmed; max 5,000 chars |
| `is_active` | boolean | conditionally | Writable via `PUT` by Administrator/Manager only — this is the documented reactivation path (Conventions §9). Defaults to `true` on create; not accepted on `POST` |
| `custom_fields` | object | **no (MVP)** | Rejected in writes until Phase 8 — see §2.4 |
| `created_at` / `updated_at` | timestamp | no | Server-managed |

Read-only fields supplied in any write request return `422 validation_error` (Conventions §9). Empty-string values for optional fields are normalized to `null` after trimming.

---

## 2. Contract-Level Decisions

### 2.1 Role access (MVP simplification)

The Specification's permission matrix marks Staff customer access as "permitted subset" and "configuration-dependent." Configuration does not exist until Phase 8, so the MVP fixes the behavior through the accepted Decision Log clarification dated 2026-08-16:

| Action | Administrator | Manager | Staff |
|---|---|---|---|
| `GET /customers` (list/search) | ✅ | ✅ | ✅ |
| `GET /customers/{id}` | ✅ | ✅ | ✅ |
| `POST /customers` | ✅ | ✅ | ❌ `403 permission_denied` |
| `PUT /customers/{id}` | ✅ | ✅ | ❌ `403 permission_denied` |
| `PUT` including `is_active` | ✅ | ✅ | ❌ |
| `DELETE /customers/{id}` | ✅ | ✅ | ❌ `403 permission_denied` |

Rationale: Staff need to identify the customer standing in front of them and see contact details for their bookings; restricting Staff to *only* customers linked to their own bookings requires a join-based visibility rule that adds real complexity for no demo value. Full read / no write is the simplest defensible MVP line. Narrowing Staff customer visibility is a future authorization extension. It is not part of the current Phase 8 commitment unless the business-configuration contract explicitly introduces it.

### 2.2 Customer email is not unique

Unlike `users.email` (globally unique, used for login), `customers.email` has **no uniqueness constraint** — per-tenant or global. Two customers may share an email (family members, a parent booking for children, a company contact). Duplicate-customer detection is a UI/search concern, not a database constraint. `duplicate_value` is therefore never returned by customer endpoints.

Customer emails are deliberately trimmed and lowercased because the MVP treats them as case-insensitive contact/search values; consistent storage improves display consistency and manual duplicate review. This normalization does not make the field unique and is not an authentication rule. Preserving display-case spelling can be revisited only if a concrete client requirement appears.

### 2.3 No customer-facing login

Customers are business records, not principals. Nothing in this contract creates credentials, sends email, or links to `users`. The future public booking flow (Specification §58) will revisit customer identity in v2.

### 2.4 `custom_fields` frozen until Phase 8

The column exists (JSONB, default `{}`), is returned in responses, and is **not writable**: any `custom_fields` key in a `POST` or `PUT` body returns `422 validation_error`, exactly like any other read-only field. Validation of custom-field values against per-business definitions is the business-configuration contract's job (Phase 8); accepting unvalidated JSON now would create data with no schema to retro-validate against. When Phase 8 lands, that contract amends this one explicitly (Conventions §1 exception rule).

### 2.5 Deactivation semantics

`DELETE` is soft deletion (Conventions §9): sets `is_active = false`, returns `204`, idempotent on repeat, tenant-scoped, works on already-inactive records. Deactivated customers remain referenced by historical bookings (Specification §41) and remain retrievable by direct `GET /{id}`. Reactivation is `PUT` with `"is_active": true` (Administrator/Manager). Hard deletion does not exist in this API.

### 2.6 Activity-record ownership and atomicity

Every customer activity record uses `business_id = authenticated_user.business_id`, `user_id = authenticated_user.id`, `entity_type = "customer"`, and `entity_id = customer.id`. The customer mutation and its required activity record commit or roll back together. An activity-log insertion failure therefore rolls back the corresponding create, update, reactivation, or deactivation rather than leaving a partially audited state.

---

## 3. `GET /customers`

**Roles:** all authenticated roles.

### Query parameters

| Parameter | Behavior |
|---|---|
| `page`, `page_size` | Shared pagination (Conventions §6) |
| `search` | Case-insensitive **literal** substring match against `name`, `email`, and `phone` (Specification §18). Trimmed; max 200 chars; empty after trimming = parameter omitted. SQL wildcard characters (`%`, `_`, and the configured escape character) are escaped before matching |
| `is_active` | `true`/`false`; **defaults to `true`** (Conventions §7) |
| `sort` | Whitelist: `name`, `created_at`. Default: `name` ascending. The server appends `id ASC` as the deterministic tie-breaker for every permitted sort |

Unknown or malformed parameters → `422 validation_error`. Phone search matches the stored string as-is; the MVP does not normalize phone formats for matching (documented limitation — searching `03001234567` will not find `+92 300 1234567`). The authoritative DBML's current B-tree customer indexes remain the MVP baseline; trigram or other specialized substring-search indexes are added only if measured query performance justifies them.

### Success — `200 OK`

Shared pagination envelope; `data` is an array of §1 representations. Empty result → `"data": []`, never `404`.

---

## 4. `POST /customers`

**Roles:** Administrator, Manager.

### Request body

```json
{
  "name": "Fatima Noor",
  "email": "Fatima@Example.test",
  "phone": "+92 300 1234567",
  "address": null,
  "notes": null
}
```

Only `name` is required; optional fields may be omitted entirely or sent as `null` (equivalent). Unknown fields, `custom_fields`, `is_active`, or any read-only field → `422 validation_error`.

### Behavior

Validate → normalize (§1.1) → insert with `business_id` from the authenticated principal → write activity log (`action = "customer.create"`, `entity_type = "customer"`, `entity_id = <new id>`) atomically with the insert → return the persisted resource.

### Success — `201 Created`

Full §1 representation; `Location: /api/v1/customers/{id}`.

### Errors

| Case | Response |
|---|---|
| Validation/normalization failure, read-only or unknown fields | `422 validation_error` (with `fields` entries) |
| Staff role | `403 permission_denied` |

---

## 5. `GET /customers/{id}`

**Roles:** all authenticated roles.

Returns the §1 representation. Inactive customers **are** returned (Conventions §7 — direct lookups may return inactive records; the frontend renders the inactive state). Malformed UUID in the path → `422 validation_error`. Nonexistent or cross-tenant `id` → `404 not_found`.

---

## 6. `PUT /customers/{id}`

**Roles:** Administrator, Manager.

Complete replacement of client-writable fields (Conventions §9): `name`, `email`, `phone`, `address`, `notes`, `is_active`. All six must be present; omitting any returns `422 validation_error` naming the missing field. This is deliberate PUT semantics — clients send back the full editable representation.

### Behavior

Validate → normalize → tenant-scoped guarded update → activity log (`action = "customer.update"`; use `"customer.reactivate"` / `"customer.deactivate"` only when the update changes `is_active`) atomically → return the updated resource. A `PUT` that changes `is_active` writes exactly one transition activity record (`customer.reactivate` or `customer.deactivate`), even when other customer fields change in the same request; it does **not** also write a separate `customer.update` record. State comparison and the corresponding transition audit use a row lock or equivalent guarded write so competing requests cannot record the same state transition twice. Updating an inactive customer is permitted (that is how reactivation works). `updated_at` is refreshed server-side.

### Success — `200 OK` with the full updated representation.

### Errors

| Case | Response |
|---|---|
| Missing writable field, invalid value, read-only/unknown field | `422 validation_error` |
| Staff role | `403 permission_denied` |
| Nonexistent or cross-tenant id | `404 not_found` |

---

## 7. `DELETE /customers/{id}`

**Roles:** Administrator, Manager.

Soft deletion per §2.5. Sets `is_active = false`; writes activity log (`action = "customer.deactivate"`) atomically **only when the state actually changes** — a repeated `DELETE` returns `204` again but does not write a duplicate audit record.

The active-to-inactive transition uses a guarded update or row lock. One valid implementation is `UPDATE ... WHERE id = :id AND business_id = :business_id AND is_active = true RETURNING id`; only a returned row produces the deactivation activity record. If no row is returned, a tenant-scoped existence check that includes inactive records distinguishes an already-inactive customer (`204`) from a nonexistent or cross-tenant identifier (`404`). Concurrent deactivation requests for the same own-tenant customer therefore all return `204`, while exactly one deactivation activity record is created.

### Success — `204 No Content`, no body.

### Errors

| Case | Response |
|---|---|
| Staff role | `403 permission_denied` |
| Nonexistent or cross-tenant id | `404 not_found` |
| Malformed UUID | `422 validation_error` |

---

## 8. Interaction With Bookings

- Deactivating a customer does **not** cancel or modify their existing bookings; those follow the booking state machine independently.
- Whether an inactive customer can receive **new** bookings is the bookings contract's rule, not this one's. (Expected: rejected with `409`; final say belongs to the bookings contract.)
- If the bookings contract rejects new bookings for inactive customers, its active-customer validation must be transaction-safe relative to concurrent customer deactivation; the exact locking or guarded-write strategy belongs to that contract.
- Customer booking history is retrieved via `GET /bookings?customer_id={id}`, not embedded here.

---

## 9. Required Automated Tests

1. Create with all fields, create with only `name` → 201, correct persisted values, `Location` header, `custom_fields = {}`, activity log written.
2. Create/update normalization: email lowercased and trimmed, name trimmed, empty strings → `null`.
3. Validation failures: missing `name`, name > 200 chars, invalid email, oversized `phone`/`address`/`notes`, `custom_fields` in body, `is_active` on POST, unknown field — each `422` with correct `fields` path.
4. Staff role: list and detail succeed; POST, PUT, DELETE each `403 permission_denied`.
5. Search matches name, email, and phone independently; search is case-insensitive; `%`, `_`, and the configured escape character are treated literally; search plus `is_active=false` composes.
6. List default excludes inactive customers; `is_active=false` returns only inactive; direct GET returns an inactive customer.
7. Sort by `name` and `-created_at`; unsupported sort field → `422`; deterministic order with duplicate primary values using the documented `id ASC` tie-breaker.
8. Pagination: page beyond results → empty `data` with valid metadata.
9. PUT replaces all writable fields; PUT omitting one writable field → `422`; PUT with `is_active: true` reactivates; a PUT that changes `is_active` and other fields writes exactly one transition activity record (`customer.reactivate` or `customer.deactivate`) and no additional `customer.update` record.
10. DELETE deactivates → 204; sequential repeat DELETE → 204; concurrent double-DELETE → both requests return 204; in both cases **exactly one** deactivation audit record exists and historical bookings still reference the customer.
11. Cross-tenant: GET/PUT/DELETE against another tenant's customer id → `404 not_found` with a body indistinguishable from a truly nonexistent id; cross-tenant records never appear in lists, searches, or counts.
12. Two customers with the same email in one tenant → both created successfully (no uniqueness).
13. Protected-route wiring: missing token, invalid token, expired token, and a valid token for an inactive user or business produce the inherited Auth Contract §4 errors on customer endpoints.
14. Strict query validation: unknown parameters, malformed `is_active`, and repeated parameters where disallowed → `422 validation_error`.
15. Audit atomicity: if the required activity-log insertion fails, customer create, update, reactivation, and deactivation each roll back completely.

---

*FINAL — verified against the Shared API Conventions, Authentication API Contract, Specification v1.2, and authoritative DBML on 2026-08-16. Next artifacts: staff (including availability windows), services, then bookings (state machine + availability-window coalescing).*
