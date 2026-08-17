---
paths:
  - "frontend/src/**/*.{ts,tsx}"
  - "frontend/*.{ts,json}"
---

# Frontend rules

React + TypeScript + Vite + Tailwind + TanStack Query. Strict TypeScript; no `any` on a boundary,
no `@ts-ignore` without a comment naming the reason.

## Auth session

- Access token lives **in memory only**.
- Refresh token lives in `sessionStorage`. **Never `localStorage`** — this is a documented,
  deliberate decision with a documented XSS trade-off.
- Exactly one refresh in flight at a time; queue concurrent 401s behind it.
- Logout clears both plus the query cache.

## Server is the authority

Role-based UI hiding is a convenience, never a control. Every screen must handle an authoritative
`401`, `403`, `404`, `409`, and `422` arriving anyway, and render correctly when it does.

Branch on the machine-readable **error code**, never on the human-readable message text. Map the
`fields` array to form controls; keep a safe general fallback for unmapped errors.

## Types

Frontend types derive from the approved OpenAPI schema. Do not hand-write a response interface that
drifts from the contract — regenerate.

## Data specifics

- Price is a decimal **string** end to end. Never parse it into a JS number for storage, arithmetic,
  or round-tripping. Currency is derived from the business, never sent by the client.
- Display times in the business timezone; send offset-aware timestamps.
- Availability is a whole-week atomic replacement, not per-row edits. Tell the user that saving
  canonicalizes overlapping and touching windows.
- Status changes and reschedule/reference changes are **separate requests** and separate UI actions.
  Never combine them in one submit.
- Duplicate customer emails and duplicate service names are valid data, not errors.

## Query cache

Stable query keys by resource plus filter set. After a mutation, invalidate only the affected views.
Deactivation and status transitions must not leave stale active/inactive or booking-range data on
screen.

## Structure and accessibility

Feature-sliced under `src/features/<domain>/`; `src/pages/` is routed composition only; shared
primitives in `src/components/`. Every interactive element is keyboard reachable with a visible focus
ring, a real label, and an error message associated to its input. Target WCAG 2.2 AA.
