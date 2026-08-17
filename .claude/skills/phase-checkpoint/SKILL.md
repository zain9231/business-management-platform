---
name: phase-checkpoint
description: Run a phase exit gate — full regression, gate criteria, deployment check where applicable, and the checkpoint tag.
argument-hint: "<phase> e.g. 2"
disable-model-invocation: true
---

# Phase $ARGUMENTS exit gate

A phase gate is the point where continuing on a broken foundation stops being recoverable. Be strict.

## 1. Read the gate

Find the phase's exit gate line and its milestone row in
`docs/project/implementation-backlog.md` §3. Quote the required outcome verbatim. That sentence, not
your judgment, is the pass criterion.

## 2. Confirm every task in the phase is closed

List each task id in the phase with its checklist state. An unchecked item is an open gate.

## 3. Full regression

```bash
cd backend && ruff format --check . && ruff check . && mypy app
cd backend && alembic upgrade head && alembic downgrade base && alembic upgrade head
cd backend && pytest -v
```

From Phase 6 onward, add the frontend component suite and the browser-level workflow tests.

Run migrations from an empty database to head **twice** — once locally and once in CI — where the
gate requires it. Paste all real output.

## 4. Contract suites

Re-run every contract suite accepted so far, not only the newest. A phase gate is a regression gate:
Phase 5 must not break Phase 3.

## 5. Adversarial sweep

`tenant-isolation-auditor` and `security-reviewer` across everything implemented so far, in fresh
context. From Phase 5, add `concurrency-reviewer`.

## 6. Deployment

Where the phase includes or follows a deployment gate, verify remotely: liveness, readiness,
migration version, HTTPS, CORS, restart persistence, and one deliberate cross-tenant attempt that
returns an indistinguishable `404` without affecting counts.

## 7. Verdict and tag

State **PASS** or **FAIL** in one line.

On PASS, add a row to `docs/project/progress.md` for the phase gate, then propose the annotated tag
and record what it covers:

```bash
git tag -a phase-<n>-complete -m "Phase <n> exit gate passed on <date>. <evidence summary>"
git push origin phase-<n>-complete
```

On FAIL, list the blockers in order and stop. Do not start the next phase. Do not reclassify a
blocker as polish.
