---
name: contract-gate
description: Run a full API contract acceptance gate — the complete numbered test suite, the shared conventions checklist, adversarial review, and the OpenAPI check.
argument-hint: "<resource> e.g. customers | auth | staff | services | bookings | users"
disable-model-invocation: true
---

# Contract gate — $ARGUMENTS

A gate is pass/fail. Do not soften a failure, and do not change a test to make it pass.

## 1. Run the full suite against real PostgreSQL

```bash
cd backend && pytest tests/contract/test_$ARGUMENTS_contract.py -v
```

Then the whole suite, including markers the fast loop skips:

```bash
cd backend && pytest -v
```

Paste the real output. Never assert success without it.

## 2. Prove numbered coverage

Build the table: `contract test number → test function → pass/fail`. Read the numbered test list in
`docs/api/contracts/$ARGUMENTS-api-contract.md` and confirm **every** number has a function. A number
with no test is a gate failure, not a note for later.

## 3. Shared conventions checklist

Walk `docs/api/shared-api-conventions.md` against the resource: error envelope and the full code
registry, strict input rejection, pagination envelope and bounds, whitelisted sorting with `id ASC`
tie-break, literal search escaping of `%` / `_` / the escape character, deterministic responses,
audit vocabulary.

## 4. Adversarial review in fresh context

Run these subagents on the resource and report their findings verbatim:

- `contract-auditor` — clause-by-clause compliance
- `tenant-isolation-auditor` — every operation scoped, `404` indistinguishable
- `security-reviewer` — disclosure and authorization
- `concurrency-reviewer` — only if this resource takes locks or rotates tokens

Tell each to report only gaps affecting correctness or a stated requirement.

## 5. OpenAPI

Generate the schema and confirm it matches the approved shapes, status codes, and — for services —
canonical decimal-string price and derived currency. A drifting OpenAPI is a gate failure.

## 6. Verdict

State **PASS** or **FAIL** in one line, then the evidence.

On PASS: record the checkpoint per the backlog and update the traceability matrix if a mapping
changed. On FAIL: list what blocks it, ordered, and stop. Do not continue to the next phase.
