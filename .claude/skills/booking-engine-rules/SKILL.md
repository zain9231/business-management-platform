---
name: booking-engine-rules
description: The booking engine's hard rules — canonical lock order, half-open overlap, availability containment, cross-midnight joins, DST materialization, and the state machine. Use whenever touching bookings, staff availability, or anything that locks rows.
---

# Booking engine rules

**Not authoritative.** `docs/api/contracts/bookings-api-contract.md` and
`docs/api/contracts/staff-api-contract.md` are. This is the map of the parts that are easy to get
subtly wrong, with the sections to read.

## Canonical lock order — never deviate

1. booking row (on PUT)
2. customer row
3. staff row(s), **ascending by UUID**
4. service row

The **staff row is the serialization point** for create and reschedule overlap decisions. Availability
replacement and customer/staff/service deactivation must use a compatible order. Any other order is a
deadlock.

After acquiring locks, **recheck everything**: state, visibility, the Staff-to-user link, active
references, service duration, availability, and conflicts. Nothing read before the lock is trusted.

## Overlap

```
existing.start_time < candidate.end_time  AND  existing.end_time > candidate.start_time
```

Half-open. Exact adjacency is legal. Only `scheduled`, `confirmed`, and `in_progress` block. The slot
is released once a transition to completed, cancelled, or no-show commits. Every overlap query is
tenant- **and** staff-scoped.

## Intervals

`end_time` is derived from the **locked** service duration at write time, stored, and never
recomputed because the catalog changed later. It is never client-supplied. Start times are normalized
to UTC; naive, invalid, and past timestamps are rejected with a field-specific validation response.

## Availability containment

UTC intervals map into business-local dates and weekdays, then against the stored windows.

- No availability rows at all → `staff_not_bookable`.
- Rows exist but do not continuously contain the interval — including a weekday with no windows,
  a gap, or outside every window → `outside_availability`.
- Boundary containment is exact.
- A stored row never crosses midnight. An exact `24:00:00` end joins to the next day's `00:00:00`
  start into continuous availability — while real gaps stay gaps.
- Windows are canonicalized on save: sorted, with duplicate, overlapping, and touching windows on the
  same weekday coalesced into the minimal sorted union. Canonicalization is idempotent. A canonical
  no-op replacement writes **no** activity row.

## DST

- Ambiguous local boundary → **earlier** occurrence for start, **later** occurrence for end.
- Nonexistent gap boundary → advance per the contract.
- Containment is evaluated over unions of real instants.
- Duration is **elapsed real minutes**, never naive wall-clock arithmetic. Test in a real IANA zone
  across spring-forward, fall-back, and 23- and 25-real-hour days.

## State machine

Encode the transition table as a **pure service** and exhaustively unit-test it before wiring any
endpoint. `no_show` is permitted at or after `start_time`. Direct `scheduled → completed` is illegal.
`403 permission_denied` versus `409 illegal_status_transition` follows the contract's evaluation
order.

## Audit — mutually exclusive cases

Exactly one activity row per successful call: transition, **or** reschedule, **or** update. Status
combined with a customer, staff, service, or start-time change is `422` and requires two separately
audited calls. Status plus notes together produce only the transition action.

`DELETE /bookings/{id}` is `405 method_not_allowed` with no mutation and no audit row.

Before closing any booking work, run `concurrency-reviewer`.
