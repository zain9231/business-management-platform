---
paths:
  - "docs/**/*.md"
  - "docs/**/*.dbml"
  - "docs/**/*.sha256"
---

# Frozen artifact rules

Ten Phase 0 artifacts are covered by `docs/project/phase-0-artifacts.sha256`. Editing any of them
breaks the manifest and the `phase-0-complete` tag:

- `docs/project/master-specification-v1.2.docx`
- `docs/project/implementation-backlog.md`
- `docs/api/shared-api-conventions.md`
- `docs/api/contracts/authentication-api-contract.md`
- `docs/api/contracts/customers-api-contract.md`
- `docs/api/contracts/staff-api-contract.md`
- `docs/api/contracts/services-api-contract.md`
- `docs/api/contracts/bookings-api-contract.md`
- `docs/architecture/erd/source/business-management-platform-erd-v1.2.dbml`
- `docs/architecture/erd/exports/business-management-platform-erd-v1.2.pdf`

**Do not edit these to make an implementation problem go away.** A `PreToolUse` hook blocks the
write; that is the intended behavior, not an obstacle to route around.

**Task progress does not belong here.** `docs/project/progress.md` is the living, unprotected record
of what is done and what is next. Never tick a backlog checkbox to record progress — update
`progress.md` instead.

Appending a Decision Log entry, accepting a contract revision, or correcting a genuine error in the
backlog is a legitimate change — but it is a deliberate act with consequences:

1. Tell me what needs to change and why, and get an explicit go-ahead.
2. Make the edit.
3. Recompute the manifest and update `docs/project/phase-0-artifacts.sha256`.
4. Note the new manifest hash so the tag message can be reconciled.

Never batch a frozen-artifact edit into an implementation commit.

## New documents

`users-api-contract.md` (P4U-01), the dashboard contract (P7-01), the configuration contract (P8-01),
and the payments contract (P9-01) are written and accepted *before* their implementation, and added
to `docs/project/requirements-sources.md` when accepted. A contract without an accepted numbered test
list is not finished.

## Style

Follow the existing register of these documents: plain declarative sentences, no marketing language,
no emoji, no exclamation marks. Tables for enumerable rules. Never introduce a second copy of a rule
that already lives in another artifact — link to the owner instead. Two copies of a rule is exactly
the failure mode `docs/project/requirements-sources.md` exists to prevent.

Formatters and pre-commit whitespace hooks must exclude the seven protected Markdown files, per
`CONTRIBUTING.md`.
