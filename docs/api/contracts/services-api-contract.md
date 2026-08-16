# Services API Contract — Business Management Platform

**Phase 0 artifact.** Endpoint contract for `GET /services`, `POST /services`, `GET /services/{id}`, `PUT /services/{id}`, and `DELETE /services/{id}`. Written against the Shared API Conventions (FINAL — Revision 3, 2026-08-16), Authentication API Contract (FINAL, 2026-08-16), Customers API Contract (FINAL — Revision 2), Staff API Contract (FINAL — Revision 2), Specification v1.2 (Sections 5, 6.1, 8.6, 18, 19, 40, 41, 44, and 54.2), and the authoritative DBML ERD. Status: **FINAL**, verified against those artifacts on 2026-08-16.

All endpoints live under `/api/v1`, are protected, and inherit Auth Contract §4 and all applicable shared behavior without restating it. All errors use the shared envelope and registry. Every query, count, lookup, and mutation is scoped to `authenticated_user.business_id`; nonexistent and cross-tenant resources are indistinguishable `404 not_found` responses.

---

## 1. Resource Representation

```json
{
  "id": "8be30a73-5859-49cd-bac8-f6b26b1058bf",
  "name": "Classic Haircut",
  "description": "Wash, cut, and finish.",
  "duration_minutes": 45,
  "price": "35.00",
  "currency": "USD",
  "is_active": true,
  "custom_fields": {},
  "created_at": "2026-08-16T10:00:00Z",
  "updated_at": "2026-08-16T10:00:00Z"
}
```

- `business_id` is never serialized. The authenticated tenant is authoritative.
- `description` is returned explicitly as `null` when unset.
- `price` is always a fixed-scale decimal **string** with exactly two fractional digits. It is never a JSON number and never includes a symbol.
- `currency` is a server-derived ISO 4217 code read from the authenticated tenant's current `businesses.currency`; it is not stored on `services`.
- `custom_fields` is returned as stored, `{}` by default. See §2.3.

### 1.1 Field rules

| Field | Type | Writable | Rules |
|---|---|---|---|
| `id` | UUID | no | Server-generated |
| `name` | string | yes | **Required.** Trimmed; 1–200 characters after trimming |
| `description` | string \| null | yes | Optional. Trimmed; empty after trimming becomes `null`; max 5,000 characters |
| `duration_minutes` | integer | yes | **Required.** JSON integer, not boolean or string; `1`–`1,440` inclusive |
| `price` | decimal string | yes | **Required.** Canonical `0.00`–`9999999999.99`; exactly two fractional digits; no sign, grouping separators, exponent, symbol, or surrounding whitespace |
| `currency` | ISO 4217 string | no | Derived from `businesses.currency` on every response; rejected in writes |
| `is_active` | boolean | conditionally | Administrator/Manager may write it through `PUT`; defaults to `true` on create and is rejected on `POST` |
| `custom_fields` | object | **no (MVP)** | Rejected in writes until Phase 8; see §2.3 |
| `created_at` / `updated_at` | timestamp | no | Server-managed |

Read-only, unknown, or server-derived fields supplied in a write return `422 validation_error`. `duration_minutes` is not coerced from a string, boolean, or `null`; `price` is not coerced from a JSON number, `null`, or a noncanonical numeric-looking string.

The 1,440-minute duration cap is the natural upper boundary of the MVP's day-based weekly availability model. It prevents nonsensical, effectively unbookable services and bounds booking `end_time` arithmetic before the availability check.

---

## 2. Contract-Level Decisions

### 2.1 Role access

| Action | Administrator | Manager | Staff |
|---|---|---|---|
| `GET /services` | ✅ | ✅ | ✅ |
| `GET /services/{id}` | ✅ | ✅ | ✅ |
| `POST /services` | ✅ | ✅ | ❌ `403 permission_denied` |
| `PUT /services/{id}` | ✅ | ✅ | ❌ `403 permission_denied` |
| `DELETE /services/{id}` | ✅ | ✅ | ❌ `403 permission_denied` |

The Specification says Administrator and Manager manage services and Staff do not. It does not prohibit Staff reads. Staff receive full tenant-scoped service read access because services are non-sensitive operational catalog data needed to interpret and create permitted bookings; Staff receive no service write access. This is consistent with, rather than an expansion of, the matrix's “Manage services” rule. **No Decision Log entry is required because the frozen matrix is silent on service reads and this contract does not override a recorded permission.**

### 2.2 Service names are not unique

The DBML defines no unique constraint on `services.name`. A tenant may intentionally offer variants with the same display name but different duration, price, or description. Duplicate review is a list/search concern. Service endpoints therefore never return `duplicate_value` for `name`.

### 2.3 `custom_fields` frozen until Phase 8

The JSONB column exists and is returned, but any `custom_fields` key in `POST` or `PUT` returns `422 validation_error` as a read-only field. Phase 8 owns definition and value validation and must amend this contract explicitly before writes are accepted.

### 2.4 Currency is derived, not service-owned

`price` is stored as `numeric(12,2)` without a currency column. Every response pairs it with the authenticated business's **current** `businesses.currency` under Conventions §11. Clients cannot send or override `currency` here.

Changing the business currency does not perform exchange-rate conversion and does not rewrite the numeric service price. A stored `35.00` will subsequently be represented as `"35.00"` in the new business currency. The future business-settings contract owns any confirmation or repricing workflow. Stored payment currencies remain historical and are unaffected.

### 2.5 Deactivation and reactivation

`DELETE` soft-deactivates a service and returns `204`; repeated own-tenant deletion remains `204` and does not add duplicate audit records. Authorized direct `GET` still returns an inactive service. Reactivation occurs through a complete `PUT` with `"is_active": true`. Hard deletion is not exposed.

### 2.6 Audit ownership and atomicity

Every service activity record uses `business_id = authenticated_user.business_id`, `user_id = authenticated_user.id`, `entity_type = "service"`, and `entity_id = service.id`. The service mutation and required activity record commit or roll back together.

---

## 3. `GET /services`

**Roles:** all authenticated roles.

### Query parameters

| Parameter | Behavior |
|---|---|
| `page`, `page_size` | Shared pagination (Conventions §6) |
| `search` | Case-insensitive literal substring match against `name` and `description`; trimmed; max 200 characters; empty after trimming means omitted; `%`, `_`, and the configured escape character are escaped |
| `is_active` | `true` or `false`; defaults to `true` |
| `sort` | Whitelist: `name`, `duration_minutes`, `price`, `created_at`; default `name` ascending; the server appends `id ASC` as the deterministic tie-breaker |

Unknown, repeated where disallowed, or malformed query parameters return `422 validation_error`. None of the sortable fields is nullable, so null ordering is not applicable. The existing DBML indexes are the MVP baseline; substring-search or sort-specific indexes are added only after measured need.

### Success — `200 OK`

Shared pagination envelope with an array of §1 representations. An empty result is `"data": []`, never `404`.

---

## 4. `POST /services`

**Roles:** Administrator, Manager.

### Request body

```json
{
  "name": "Classic Haircut",
  "description": "Wash, cut, and finish.",
  "duration_minutes": 45,
  "price": "35.00"
}
```

`name`, `duration_minutes`, and `price` are required. `description` may be omitted or `null`. `currency`, `is_active`, `custom_fields`, other read-only fields, and unknown fields are rejected with `422 validation_error`.

### Behavior

Validate → normalize text → parse the validated decimal string without floating point → insert with the authenticated `business_id` → atomically write `service.create` → return the persisted resource with server-derived `currency`.

### Success — `201 Created`

Full §1 representation and `Location: /api/v1/services/{id}`.

### Errors

| Case | Response |
|---|---|
| Invalid/missing value, unknown field, or read-only field | `422 validation_error` with field paths |
| Staff role | `403 permission_denied` |

---

## 5. `GET /services/{id}`

**Roles:** all authenticated roles.

Returns the §1 representation, including inactive services. Malformed path UUID returns `422 validation_error`. A nonexistent or cross-tenant id returns indistinguishable `404 not_found`.

---

## 6. `PUT /services/{id}`

**Roles:** Administrator, Manager.

Complete replacement of all client-writable fields: `name`, `description`, `duration_minutes`, `price`, and `is_active`. All five keys must be present; `description` may be `null`. Omission of any key returns `422 validation_error` naming the missing field.

### Behavior

Validate → normalize → acquire a tenant-scoped row lock or equivalent guarded update → replace all writable values → atomically write an activity record → return the persisted service. `updated_at` is refreshed.

- Default action: `service.update`.
- If `is_active` changes, write exactly one `service.reactivate` or `service.deactivate` record, even when other fields also change; do not additionally write `service.update`.
- A no-op `PUT` still refreshes `updated_at` and writes one `service.update`, matching the Staff contract's row-resource behavior.
- State comparison is protected by the same lock/guard so concurrent requests cannot record the same transition twice.

Changing `duration_minutes` does not recalculate `end_time` for existing bookings; each booking retains its stored time interval. Changing `price` does not rewrite existing bookings or payments.

### Success — `200 OK`

Full updated §1 representation.

### Errors

| Case | Response |
|---|---|
| Missing/invalid writable field, unknown field, or read-only field | `422 validation_error` |
| Staff role | `403 permission_denied` |
| Nonexistent or cross-tenant id | `404 not_found` |

---

## 7. `DELETE /services/{id}`

**Roles:** Administrator, Manager.

Set `is_active = false` and atomically write `service.deactivate` only when the state changes. Use a tenant-scoped guarded update (`... WHERE is_active = true RETURNING id`) or row-lock equivalent. If no active row is returned, an inactive-inclusive own-tenant existence check distinguishes already inactive (`204`) from nonexistent/cross-tenant (`404`). Concurrent deletes all return `204` for an existing own-tenant service, with exactly one deactivation activity record.

### Success — `204 No Content`

No body.

### Errors

| Case | Response |
|---|---|
| Staff role | `403 permission_denied` |
| Nonexistent or cross-tenant id | `404 not_found` |
| Malformed UUID | `422 validation_error` |

---

## 8. Interaction With Bookings and Business Settings

- Deactivating a service does not cancel, reschedule, or otherwise mutate existing bookings.
- The bookings contract decides whether an inactive service can be used for a new booking and must make that validation transaction-safe relative to concurrent deactivation.
- Booking `end_time` is derived from the selected service duration when the booking is created or rescheduled. Later service-duration changes do not alter that stored booking interval.
- Booking responses that display service identity must remain meaningful for inactive services; clients may resolve them through direct `GET /services/{id}`.
- Service price is catalog data, not a historical booking-price snapshot. The MVP booking schema stores no quoted price. Future billing uses payment records with their own stored amount and currency.
- A business-currency change immediately changes the derived `currency` returned for every service without converting `price`; the future settings contract owns the user-facing safeguard.

---

## 9. Required Automated Tests

1. Create with all writable fields and with `description` omitted → `201`, correct defaults, fixed-scale response price, current business currency, `Location`, `custom_fields = {}`, and one `service.create` activity record.
2. Text normalization: trimmed `name`/`description`; blank description becomes `null`.
3. Duration validation: accept `1` and `1440`; reject missing, zero, negative, `1441`, fractional, string, boolean, null, or integer-overflow values with field-specific `422`.
4. Price validation: accept `"0.00"` and `"9999999999.99"`; reject JSON numbers, negative values, signs, whitespace, symbols, grouping separators, exponents, missing/excess fractional digits, leading-zero noncanonical strings, and numeric overflow with field-specific `422`.
5. Reject `currency`, `custom_fields`, `is_active` on POST, server-managed fields, and unknown fields with `422`.
6. Role access: all roles can list/detail; Staff POST/PUT/DELETE each return `403 permission_denied`.
7. Search independently matches name and description, is case-insensitive, treats `%`, `_`, and the configured escape character literally, and composes with `is_active=false`.
8. List defaults to active services; `is_active=false` lists inactive only; direct GET returns inactive.
9. Sort each allowed field ascending/descending; reject unsupported or multi-field sorts; duplicate primary values resolve deterministically with `id ASC`.
10. Pagination beyond the result set returns empty `data` with valid metadata.
11. PUT requires all five writable keys; replaces all values; can reactivate; a mixed-field state change writes exactly one transition record; a no-op writes exactly one `service.update`.
12. DELETE deactivates; repeated and concurrent deletion return `204` for the own-tenant record while exactly one deactivation activity record exists.
13. Duplicate names within one tenant are accepted; `duplicate_value` is not returned.
14. Cross-tenant list/search/count isolation and indistinguishable `404` responses for direct GET/PUT/DELETE.
15. Currency derivation: a business-currency change alters the response `currency` without altering the stored/serialized numeric price; client-supplied currency is never accepted.
16. Existing booking stability: service duration, price, and active-state changes do not modify stored existing bookings; historical payments remain unchanged.
17. Protected-route wiring: inherited missing/invalid/expired-token and inactive-account errors apply on every endpoint.
18. Audit atomicity: failure to insert the required activity record rolls back create, update, transition, and deactivation mutations completely.

---

*FINAL — verified against the finalized conventions, auth, customers, staff, Specification v1.2, and authoritative DBML on 2026-08-16. Staff read access is an explicit interpretation of a silent matrix cell and requires no Decision Log amendment. Next: the Bookings contract.*
