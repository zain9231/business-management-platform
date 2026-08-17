# Implementation Progress

**Status:** living document — this file is intentionally **not** covered by
`phase-0-artifacts.sha256` and may be edited freely.

`implementation-backlog.md` is checksum-protected, so its checkboxes cannot be ticked without
recomputing the manifest and reconciling the `phase-0-complete` tag. It stays frozen as the accepted
plan. This file records what has actually been done against it.

Update it in the same PR that completes a task.

Next task: P1-02

## Completed

| Task | Completed | Branch / PR | Evidence |
|---|---|---|---|
| Phase 0 | 2026-08-16 | tag `phase-0-complete` | Ten artifacts accepted; manifest `a84e2b1f…2cf5f8` |
| P1-01 | 2026-08-16 | `docs/protected-main-workflow` | Repo initialized; artifacts copied and checksum-verified; `.gitignore`, `.gitattributes`, `.editorconfig`, `LICENSE`, `CONTRIBUTING.md`, PR template in place; protected-main workflow documented |
| Tooling correction PR A (#6) | 2026-08-17 | `fix/issue-6-task-lifecycle-policy` | Issue-before-branch lifecycle, live-status validation, approval-gated permissions, agent capability reductions, and PR-template traceability verified |

## In progress

| Task | Started | Branch | Blocking issue |
|---|---|---|---|
| — | — | — | — |

## Deferred or reopened

| Task | Reason | Revisit at |
|---|---|---|
| — | — | — |

## Notes

- A task is complete only when its implementation, required automated tests, and affected
  documentation are committed together, per backlog §2.
- Record the PR number and the evidence that satisfied the task's contract coverage, not just a date.
- Phase exit gates get their own row with the annotated tag name.
