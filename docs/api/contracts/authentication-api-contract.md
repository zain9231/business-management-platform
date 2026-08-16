# Authentication API Contract — Business Management Platform

**Phase 0 artifact.** Endpoint contract for `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`, and `POST /auth/logout`. Written against the Shared API Conventions (FINAL — Revision 3, 2026-08-16) and Specification v1.2 (Sections 16, 48, 54.1) and the Decision Log entries of 2026-08-15/16 (JWT access/refresh with rotation, hashed refresh-token persistence, server-side revocation, `POST /auth/logout` added, email globally unique). Status: **FINAL** — mutually verified against the Shared API Conventions on 2026-08-16.

All endpoints below live under the `/api/v1` base path. All error responses use the shared error envelope and error-code registry. Unknown body fields and unknown query parameters return `422 validation_error` per the conventions.

---

## 1. Token Model

### 1.1 Access token

- Format: JWT, signed with **HS256** using a server-side secret from the environment (`JWT_SECRET`). `JWT_SECRET` must contain at least 32 cryptographically random bytes; application startup fails for a missing, placeholder, or shorter secret. Asymmetric signing and managed key rotation are future extensions.
- Claims: `iss` (configured issuer), `aud` (configured API audience), `sub` (user UUID as string), `type` = `"access"`, `jti` (UUID), `iat`, `exp`. **No role, email, or business claim is embedded.**
- Lifetime: **15 minutes** by default, configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Verification pins the accepted algorithm to `HS256`; the decoder never trusts or derives its algorithm allowlist from the token header. It requires and validates `iss`, `aud`, `sub`, `type`, `jti`, `iat`, and `exp`; `sub` and `jti` must parse as UUIDs. Missing, malformed, or mismatched claims produce `401 invalid_token`.
- On every protected request the server decodes and verifies the token, then **loads the user row from the database**. A correctly signed token whose `sub` no longer resolves to a user returns `401 invalid_token`. Role, `business_id`, and active status are always taken from the database, never from token claims. Rationale: tenant-scoped queries hit the database anyway, this keeps role changes and deactivation effective within one request rather than one token lifetime, and it directly implements the inactive-user/inactive-business rejection required by Conventions §3.
- Clock skew leeway: **0 seconds**. The MVP runs server-side verification only; no distributed clock tolerance is needed.

### 1.2 Refresh token

- Format: JWT, HS256, same secret and common required claims as the access token; `type` = `"refresh"`. Issuer, audience, algorithm, UUID, signature, and required-claim validation are identical except for the expected token type.
- Lifetime: **14 days** by default, configurable via `REFRESH_TOKEN_EXPIRE_DAYS`.
- Persistence: on issuance, the server stores a row in `refresh_tokens` containing `user_id`, `token_hash` = SHA-256 hex digest of the **raw token string**, `expires_at`, `revoked_at = NULL`. The raw token is never stored and never logged.
- A refresh token is **usable** only when: its signature and `type` verify, its `exp` has not passed, a matching `token_hash` row exists, that row's `revoked_at` is `NULL`, that row's `expires_at` has not passed, the owning user is active, and the user's business is active.
- **Rotation:** every successful `POST /auth/refresh` revokes the presented row (`revoked_at` set) and issues a new access/refresh pair, atomically in one transaction. A rotated token that is presented again is simply a revoked token and fails uniformly (§3). Token-family-wide compromise handling ("logout all devices") is post-MVP per the Decision Log.
- Expired or revoked rows may be purged by a maintenance job (Specification §44.3); purging must not change any externally observable behavior, since a missing row and a revoked row produce the same response.

### 1.3 Type confusion

An access token presented where a refresh token is required, or vice versa, fails verification (`type` mismatch) and is treated as an invalid token. No distinct error code is exposed.

### 1.4 Password hashing

- Passwords are hashed with **Argon2id** using a maintained implementation. Minimum parameters are memory cost = 19,456 KiB, time cost = 2, and parallelism = 1. Deployment-specific tuning may strengthen these settings without changing the API contract.
- `users.password_hash` stores the complete encoded Argon2id string, including its algorithm, salt, and cost parameters. Plaintext and reversible password storage are forbidden.
- Passwords are compared exactly as submitted—no trimming, case conversion, or Unicode rewriting. Authentication and user-creation schemas enforce the same maximum of 1,024 UTF-8 bytes; larger values return `422 validation_error`.
- Verification uses the password library's safe verification function. If a user's stored parameters are weaker than the current configured minimum, the password is rehashed after a successful login within the same transaction.
- The application maintains one valid precomputed dummy Argon2id hash. When a login email does not match a user, the submitted password is still verified against this dummy hash before returning the uniform failure response, reducing account-enumeration timing differences.

### 1.5 Token response headers

Every successful response containing an access or refresh token includes:

```http
Cache-Control: no-store
Pragma: no-cache
```

Intermediaries and clients must not cache token responses.

---

## 2. `POST /auth/login`

**Authentication:** none (documented unauthenticated exception). **Roles:** n/a.

### Request body

```json
{
  "email": "owner@demosalon.test",
  "password": "correct horse battery staple"
}
```

- `email`: required, trimmed, lowercased before lookup (Conventions §2 normalization), must be a syntactically valid email, max 320 chars.
- `password`: required, non-empty, maximum 1,024 UTF-8 bytes. No trimming—passwords are matched byte-exact as submitted.

### Behavior

1. Validate the body (`422 validation_error` on failure).
2. Look up the user by normalized email. Email is globally unique, so no tenant context is needed—this is the reason for the global-uniqueness decision.
3. Verify the password against `password_hash`; when no user exists, perform the dummy-hash verification required by §1.4 before continuing to the uniform failure.
4. Reject when the user does not exist, the password is wrong, the user is inactive, **or the user's business is inactive** — all four cases return the **identical** response: `401 invalid_credentials` with message `"Invalid email or password."` Neither account existence nor account/business status is distinguishable through status code, error code, message, timing-relevant response body, or headers. (`inactive_account` is deliberately **not** used at login; see §5.)
5. On success, atomically: update `users.last_login`, insert the new `refresh_tokens` row, and write an activity-log entry (`business_id = <user business id>`, `user_id = <user id>`, `action = "auth.login"`, `entity_type = "user"`, `entity_id = <user id>`).
6. Return the token pair.

### Success — `200 OK`

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 900
}
```

- `expires_in` is the access-token lifetime in seconds.
- The response contains no user object. Clients call `GET /auth/me` after login; this keeps one authoritative representation of the current user.
- The response includes the `Cache-Control: no-store` and `Pragma: no-cache` headers required by §1.5.

### Errors

| Case | Response |
|---|---|
| Body validation failure | `422 validation_error` |
| Unknown email / wrong password / inactive user / inactive business | `401 invalid_credentials` (uniform) |
| Login-abuse control triggered (if implemented pre-deployment) | `429 rate_limited` |

Failed login attempts are recorded in structured application logs (without the password) — not in `activity_logs`.

---

## 3. `POST /auth/refresh`

**Authentication:** none — no `Authorization` header is required or inspected; the refresh token in the body is the sole credential (documented unauthenticated exception). **Roles:** n/a.

### Request body

```json
{
  "refresh_token": "<jwt>"
}
```

### Behavior

1. Validate the body (`422 validation_error` if the field is missing or not a string — this covers request *shape* only).
2. Evaluate usability per §1.2.
3. **Uniform failure:** malformed, forged, expired, revoked, previously rotated, or unknown tokens, and tokens whose owning user or business is inactive, all return the identical `401 invalid_token` with message `"Invalid or expired session. Please sign in again."` The server may record the specific internal reason in structured logs; it is never exposed to the caller (Conventions §5).
4. On success, atomically in one transaction: set `revoked_at` on the presented row, insert the new row, and issue a new access/refresh pair.
5. No activity-log entry is written for routine refresh; it is an infrastructure event, not a business action.

### Success — `200 OK`

Same body shape and no-cache headers as login: new `access_token`, new `refresh_token`, `token_type`, `expires_in`, `Cache-Control: no-store`, and `Pragma: no-cache`.

### Errors

| Case | Response |
|---|---|
| Missing/non-string `refresh_token`, unknown fields | `422 validation_error` |
| Every other failure, without distinction | `401 invalid_token` (uniform) |

### Concurrency

Two concurrent refresh calls presenting the same token must not both succeed. The rotation update uses a guarded write (`UPDATE … SET revoked_at = now() WHERE token_hash = :h AND revoked_at IS NULL` and row-count check, or equivalent row locking). The loser of the race receives the uniform `401 invalid_token`.

---

## 4. `GET /auth/me`

**Authentication:** required (`Authorization: Bearer <access_token>`). **Roles:** any authenticated role.

### Behavior

Returns the authenticated user's own representation, loaded fresh from the database. Read-only; no query parameters; unknown query parameters return `422 validation_error`.

### Success — `200 OK`

```json
{
  "id": "8f14e45f-ea5e-4b8b-9a0b-1234567890ab",
  "name": "Ayesha Khan",
  "email": "owner@demosalon.test",
  "role": "administrator",
  "business": {
    "id": "c9f0f895-15b4-4dd0-83b7-1234567890ab",
    "name": "Demo Salon",
    "timezone": "Europe/London",
    "currency": "USD"
  },
  "last_login": "2026-08-16T09:12:44Z",
  "created_at": "2026-08-01T10:00:00Z",
  "updated_at": "2026-08-16T09:12:44Z"
}
```

- `role` is the role **name** (`administrator` | `manager` | `staff`), lowercase, from the joined `roles` row.
- The embedded `business` object exists so the frontend can boot (timezone/currency display) without a second call. `business.id` appears in **responses only**; per Conventions §3 it is never accepted from the client for authorization.
- `password_hash` never appears in any response, here or anywhere else.
- `last_login` is nullable and returned explicitly as `null` before first tracked login.

### Errors

| Case | Response |
|---|---|
| Missing/malformed `Authorization` header | `401 authentication_required` + `WWW-Authenticate: Bearer` |
| Bad signature, unsupported algorithm, missing/malformed required claim, wrong issuer/audience/type, garbage token, invalid UUID claim, or valid signature whose `sub` has no user row | `401 invalid_token` + `WWW-Authenticate: Bearer` |
| Expired access token | `401 token_expired` + `WWW-Authenticate: Bearer` — distinguished so the client knows a silent refresh is worth attempting (Conventions §5) |
| Token valid but user or business deactivated | `403 inactive_account` (see §5) |

These four rows define the **shared protected-endpoint authentication behavior** referenced by Conventions §2/§3: every protected endpoint in every contract inherits them without restating them.

---

## 5. `POST /auth/logout`

**Authentication:** none — like refresh, the refresh token in the body is the sole credential (documented unauthenticated exception). Rationale: a user whose access token has already expired must still be able to log out without first performing a refresh round-trip; and possession of a refresh token already confers the ability to *use* the session, so the strictly weaker ability to *destroy* it needs no additional proof. **Roles:** n/a.

### Request body

```json
{
  "refresh_token": "<jwt>"
}
```

### Behavior

1. Validate the body (`422 validation_error`).
2. Evaluate the token per §1.2 usability rules, with one difference from refresh: an inactive user or inactive business does **not** block revocation — if a matching, unrevoked, unexpired row exists, revoke it. (Destroying a session for a deactivated account is always desirable.)
3. On success, atomically in one transaction: set `revoked_at` and write an activity-log entry (`business_id = <user business id>`, `user_id = <owning user id>`, `action = "auth.logout"`, `entity_type = "user"`, `entity_id = <owning user id>`). After commit, return `204 No Content` with no body.
4. Per the Decision Log (2026-08-16): a token that is malformed, forged, expired, already revoked, or previously rotated returns `401 invalid_token` — the same uniform response as refresh. Logout is therefore **not** idempotent at the HTTP level: the second identical logout call returns `401`. Clients should treat a `401` from logout as "already logged out" and clear local state regardless.
5. "Logout all devices" is post-MVP per the Decision Log; this endpoint revokes exactly the presented token's row.

### Errors

| Case | Response |
|---|---|
| Missing/non-string `refresh_token`, unknown fields | `422 validation_error` |
| Every token failure, without distinction | `401 invalid_token` (uniform) |

---

## 6. Error-Code Usage Summary

| Code | Where it is used in auth |
|---|---|
| `invalid_credentials` | Login only — uniform for unknown email, wrong password, inactive user, inactive business |
| `authentication_required` | Protected endpoints, missing/malformed `Authorization` header |
| `invalid_token` | Protected endpoints (bad access token); refresh and logout (uniform for all refresh-token failures) |
| `token_expired` | Protected endpoints only, expired access token — signals that silent refresh may succeed |
| `token_revoked` | **Not used in the MVP.** Exposing revoked-vs-expired on the refresh path is exactly the distinction Conventions §5 forbids; the code stays in the registry (registry codes are never removed) but no MVP endpoint returns it |
| `inactive_account` | Protected endpoints only — valid access token, but user or business was deactivated after issuance; `403` because the identity authenticated successfully and re-presenting credentials cannot cure it |
| `validation_error` | Request-shape failures on all four endpoints |
| `rate_limited` | Login abuse control, if implemented before public deployment |

The `403 inactive_account` vs `401 invalid_credentials` asymmetry is intentional: at **login**, account status is concealed because the caller has not proven anything; on a **protected request**, the caller holds a token the server itself issued, so confirming deactivation leaks nothing new and gives the frontend a clean "sign out and show 'account disabled'" path.

---

## 7. Security Notes (contract-level obligations)

- Raw refresh tokens exist only in transit and in the client; the database stores SHA-256 hashes, and no token (access or refresh) may appear in application logs, activity logs, or error messages.
- `JWT_SECRET`, issuer, and audience come from deployment configuration. The secret is never committed or logged and differs between development and production. Issuance and verification must use exactly the same configured issuer and audience.
- The MVP deliberately returns the refresh token in JSON rather than an HttpOnly cookie, preserving the bearer-token API decision and avoiding cookie/CSRF complexity. The React client stores the access token in memory and the refresh token in `sessionStorage`, never `localStorage`; both are cleared on logout, and the refresh token also disappears when the tab session ends. Because `sessionStorage` remains JavaScript-readable, XSS can still steal the refresh token. This accepted MVP limitation must appear in the README. Moving the refresh token to a `Secure`, `HttpOnly`, appropriately `SameSite` cookie is post-MVP hardening and requires an explicit contract revision plus CSRF/CORS rules.
- Login and refresh are the natural targets for abuse controls. Rate limiting is not an MVP gate, but per Specification §48 it must be considered before public deployment; the `429 rate_limited` slot above reserves the behavior.
- All four endpoints are exempt from tenant scoping in the usual sense (login/refresh/logout have no tenant context yet; `/auth/me` is self-scoped), but `/auth/me` must still resolve role and business through the user's own `business_id` — it must never accept identifiers from the client.
- HTTPS is assumed in deployed environments; bearer tokens over plaintext HTTP are acceptable only in local development.

---

## 8. Required Automated Tests

Authentication (Specification §54.1, Conventions §12):

1. Valid credentials → 200, well-formed pair, required claims/issuer/audience present, `expires_in` matches config, no-cache headers present, `last_login` updated, `refresh_tokens` row created with correct hash and expiry, activity log written.
2. Wrong password, unknown email, inactive user, inactive business → four separate tests all asserting **byte-identical** `401 invalid_credentials` envelopes; a unit test also confirms the dummy Argon2id verification path executes for an unknown email.
3. Refresh with a valid token → 200 new pair; old row `revoked_at` set; new row created; old token now fails.
4. Refresh reuse after rotation, refresh with expired token, refresh with forged signature, refresh with an access token in the refresh slot, refresh for a deactivated user → all uniform `401 invalid_token`.
5. Concurrent double-refresh of the same token → exactly one success (transaction/race test).
6. `/auth/me` happy path per role (administrator, manager, staff) → correct `role` string and business object; no `password_hash` anywhere in the body.
7. `/auth/me` with missing header, garbage token, expired token, valid token for a nonexistent user, and valid token for a since-deactivated user → `authentication_required`, `invalid_token`, `token_expired`, `invalid_token`, and `403 inactive_account` respectively; `WWW-Authenticate: Bearer` present on the 401s.
8. Logout happy path → 204, row revoked and activity log written in one transaction; the revoked refresh token then fails refresh; the still-valid access token continues to work until expiry (documented and asserted—access tokens are not revocable in the MVP).
9. Logout replay of the same token → `401 invalid_token`.
10. Logout for a deactivated user with an otherwise-valid token → 204 (revocation permitted).
11. Unknown body fields on all POST bodies → `422 validation_error`.
12. Email normalization: login with `"  Owner@DemoSalon.TEST "` succeeds against a stored lowercase email.
13. Unsupported or `none` JWT algorithm, missing required claim, malformed UUID claim, and incorrect issuer or audience → uniform `401 invalid_token`.
14. Unknown query parameters on all four endpoints → `422 validation_error`.
15. Concurrent double-logout using the same refresh token → exactly one `204`; the loser receives uniform `401 invalid_token`; exactly one logout activity record exists.
16. Login and refresh responses include `Cache-Control: no-store` and `Pragma: no-cache`.
17. Password input over 1,024 UTF-8 bytes → `422 validation_error`; no password hash verification is attempted.
18. If login audit insertion fails, the `last_login` update and refresh-token insertion roll back; if logout audit insertion fails, revocation rolls back.

Test 8's second half doubles as the documented MVP limitation: **revocation applies to refresh tokens only; an access token remains valid until `exp`** (≤ 15 minutes). This is the standard trade-off of stateless access tokens and is stated in the README's known-limitations section.

---

*FINAL—mutually verified against Shared API Conventions §§1–5, 9, 11–12 on 2026-08-16. Next artifacts (Week 2): customers, staff (including availability), services, and bookings contracts. The bookings contract carries the status state machine and the availability-window coalescing rule agreed on 2026-08-16.*
