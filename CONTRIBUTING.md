# Contributing

This repository is currently developed as a portfolio project. The workflow is intentionally lightweight, but changes must remain traceable to the accepted specification, API conventions, endpoint contracts, or implementation backlog.

## Source of truth

Before changing behavior, consult:

- `docs/project/requirements-sources.md` for scoped artifact authority;
- `docs/project/implementation-backlog.md` for task order and acceptance gates;
- `docs/api/shared-api-conventions.md` for cross-cutting API behavior; and
- the applicable endpoint contract in `docs/api/contracts/`.

Material changes to frozen scope or architecture require an explicit documented exception and, when applicable, a Decision Log entry in the master specification.

## Branch workflow

- Keep `main` in a working, reviewable state.
- Create a focused branch for each backlog task or tightly related correction.
- Use branch names such as `feat/p3-01-jwt-issuance`, `fix/tenant-filter`, `test/auth-refresh-rotation`, or `docs/readme-setup`.
- Open a pull request before merging to `main`, even when working alone, once repository protection is configured.
- Do not combine unrelated backlog tasks in one branch.

## Commit messages

Use short imperative messages with a Conventional Commits-style prefix:

- `feat: add customer creation endpoint`
- `fix: prevent cross-tenant customer access`
- `test: add refresh-token rotation coverage`
- `docs: document local Docker setup`
- `chore: configure repository tooling`

Keep commits atomic: one coherent change and its required tests or documentation per commit.

## Before requesting review

- Run the formatting, linting, type-checking, migration, and test commands defined for the current phase.
- Add or update tests required by the owning contract.
- Confirm tenant-scoped reads, writes, filters, and counts remain isolated.
- Update setup instructions, limitations, architectural notes, and backlog status when the change affects them.
- Keep secrets, local environment files, generated output, stale downloads, and numbered duplicate artifacts out of Git.

Tool-specific commands will be added to the README as the backend, frontend, Docker, and CI scaffolds are implemented.

## Protected Phase 0 baseline

The Phase 0 checksum manifest protects the accepted specification, implementation backlog, shared API conventions, five finalized API contracts, authoritative DBML, and ERD PDF.

Do not run automatic whitespace or end-of-file fixes over those manifest-backed files. When P1-05 introduces `.pre-commit-config.yaml`, its formatting hooks must exclude exactly the seven protected Markdown files with:

`^docs/(api/shared-api-conventions\.md|api/contracts/(authentication|customers|staff|services|bookings)-api-contract\.md|project/implementation-backlog\.md)$`

Configure `check-added-large-files` with `--maxkb=2048` so the accepted 1,024,807-byte ERD PDF is allowed while unexpectedly large additions remain blocked.

After introducing or changing formatting, line-ending, or pre-commit tooling, verify the Phase 0 manifest again from a clean checkout.
