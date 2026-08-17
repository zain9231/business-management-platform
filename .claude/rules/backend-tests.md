---
paths:
  - "backend/tests/**/*.py"
  - "backend/conftest.py"
---

# Test rules

Tests run against **real PostgreSQL**. SQLite is not an acceptable substitute — the schema depends on
JSONB, enums, check constraints, composite foreign keys, and row locking.

## Traceability

Contract tests are numbered in their contract. Keep the number visible so the traceability matrix in
`docs/project/implementation-backlog.md` §4 stays auditable:

```python
def test_c07_login_unknown_email_is_byte_identical_to_wrong_password(...):
    """Auth Contract test 1 — uniform credential failure."""
```

Name the file after the resource (`tests/contract/test_bookings_contract.py`) and reference the
contract test number in the docstring. A contract test group is not "done" until every numbered case
in it has an assertion.

## Order of work

Write the failing test first. Show me it failing, then implement, then show it passing. A test that
has never failed proves nothing.

## What every mutating endpoint needs

- Success shape: exact status code, exact field set, `Location` header where contracted.
- Authorization: each of Administrator, Manager, Staff — allowed and denied paths.
- Authentication: missing, malformed, expired, wrong-type token; inactive user; inactive business.
- Tenant isolation: a deliberate cross-tenant id in the path, in a filter, and **inside the request
  body** — each returns `404`, and counts are unaffected.
- Strict input: unknown body field, unknown query parameter, malformed UUID.
- Audit: exactly one activity row from the approved vocabulary on success; **zero** on any failure.
- Audit rollback: inject an activity-insert failure and prove the domain write rolled back with it.

## Markers

Use `unit`, `integration`, `concurrency`, `dst`, `deployment`. The fast loop is
`pytest -m "not concurrency and not dst"`; the gate is the full suite.

## Determinism

- Two businesses and all three roles come from `factories.py`. Never hand-build a tenant inline.
- Freeze time with the shared helper. Never assert against `datetime.now()`.
- DST tests use a real IANA zone and assert on real elapsed instants, not wall-clock arithmetic.
- Concurrency tests use genuinely concurrent sessions and assert exactly one winner plus the
  contracted error for the losers — never `sleep()` to order them.
- A flaky test is a defect. Fix the nondeterminism or delete the test; never retry-wrap it.

## Isolation

Each test rolls back. Two tests must not be able to observe each other's committed data. If you need
committed state for a concurrency test, clean it up explicitly.
