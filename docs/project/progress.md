# Implementation Progress

**Status:** living document — this file is intentionally **not** covered by
`phase-0-artifacts.sha256` and may be edited freely.

`implementation-backlog.md` is checksum-protected, so its checkboxes cannot be ticked without
recomputing the manifest and reconciling the `phase-0-complete` tag. It stays frozen as the accepted
plan. This file records what has actually been done against it.

Update it in the same PR that completes a task.

Next task: P1-03

## Completed

| Task | Completed | Branch / PR | Evidence |
|---|---|---|---|
| Phase 0 | 2026-08-16 | tag `phase-0-complete` | Ten artifacts accepted; manifest `a84e2b1f…2cf5f8` |
| P1-01 | 2026-08-16 | `docs/protected-main-workflow` | Repo initialized; artifacts copied and checksum-verified; `.gitignore`, `.gitattributes`, `.editorconfig`, `LICENSE`, `CONTRIBUTING.md`, PR template in place; protected-main workflow documented |
| Tooling correction PR A (#6) | 2026-08-17 | `fix/issue-6-task-lifecycle-policy` | Issue-before-branch lifecycle, live-status validation, approval-gated permissions, agent capability reductions, and PR-template traceability verified |
| Tooling correction PR B (#8) | 2026-08-18 | `fix/issue-8-settings-safety` | Narrowed `.env` read deny to preserve `.env.example`; pinned `CLAUDE_CODE_USE_POWERSHELL_TOOL=0` with the shell-policy dependency recorded in `CLAUDE.md`; checksum manifest and settings JSON validity reverified |
| P1-02 (#10) | 2026-08-18 | `feat/p1-02-backend-scaffold` | `backend/app/` package boundaries, pinned `pyproject.toml` dependencies and generated `requirements.txt`, `create_app()` factory, `GET /health/live`; 3 unit tests (factory identity, liveness 200, `/api/v1` non-mount) failed before implementation and pass after; `ruff format --check`, `ruff check`, and `mypy app` clean; backend verified starting from `uvicorn app.main:app --reload` and answering over the network |

## In progress

| Task | Started | Branch | Blocking issue |
|---|---|---|---|
| — | — | — | — |

## Deferred or reopened

| Task | Reason | Revisit at |
|---|---|---|
| — | — | — |

## Chores

| Chore | Completed | Branch / PR | Evidence |
|---|---|---|---|
| Gitignore `backend/.claude/` session cache (#14) | 2026-08-18 | `chore/issue-14-gitignore-backend-claude` | Generalized `.gitignore`'s `.claude/.cache/` line to `**/.claude/.cache/`; `git status --porcelain --ignored` before/after shows `backend/.claude/` move from untracked to ignored, no tracked file changed classification |
| Consolidate Git/GitHub operating rules (#16) | 2026-08-19 | `docs/issue-16-git-operating-rules` | Added `docs/project/git-operating-rules.md` as the single owner of mechanical Git/GitHub command rules, labeled by provenance; removed the bundled `gh pr merge --squash --delete-branch` restatement from `CLAUDE.md:85`, `CONTRIBUTING.md:70`, `.claude/skills/ship-task/SKILL.md:113`, and `.claude/hooks/guard_git.py:19-21`/`:37` (message strings only, matcher/blocking logic unchanged — confirmed by diff); documented the guard's inverted coverage as a post-P1-07 deferred item |

## Notes

- A task is complete only when its implementation, required automated tests, and affected
  documentation are committed together, per backlog §2.
- Record the PR number and the evidence that satisfied the task's contract coverage, not just a date.
- Phase exit gates get their own row with the annotated tag name.
- P1-07 must add `--generate-hashes` to the `pip-compile` invocation that produces
  `backend/requirements.txt`. Pinning by version (P1-02) establishes trust once, at generation time;
  hash pinning verifies it on every install thereafter. That is where residual supply-chain risk on
  the pinned dependency set actually closes.
