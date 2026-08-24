# Business Management Platform

Contract-first, multi-tenant modular monolith for appointment-based service businesses.
FastAPI + PostgreSQL + SQLAlchemy/Alembic backend; React + TypeScript + Vite + TanStack Query frontend.
Portfolio and future commercial product — treat every commit as reviewable by a hiring manager.

## Authority — read this before changing behavior

Never invent behavior. Every field, status code, permission, constraint, and transition is already
specified. When you need a rule, read the owning artifact:

| Subject | Authoritative artifact |
|---|---|
| Post-freeze decisions | Decision Log inside `docs/project/master-specification-v1.2.docx` |
| Cross-cutting API behavior | `docs/api/shared-api-conventions.md` |
| One endpoint's fields/permissions/filters/transitions | the matching file in `docs/api/contracts/` |
| Schema, constraints, indexes, checks, delete rules | `docs/architecture/erd/source/business-management-platform-erd-v1.2.dbml` |
| Frozen scope not delegated above | `docs/project/master-specification-v1.2.docx` |
| Task order, dependencies, gates | `docs/project/implementation-backlog.md` |

Full rules: `docs/project/requirements-sources.md`.

**The ERD PDF is a viewing export. Never implement from it.** The `.dbml` wins, always.

**Conflicts are not resolved by ranking.** If two artifacts disagree, STOP. Identify which artifact
owns the subject, tell me, and propose a Decision Log entry. Do not pick one and continue.

## Non-negotiables

- **Tenant scoping is in the query, not the code path.** Every read, write, count, relationship check,
  lock, and mutation on tenant-owned data filters by the authenticated user's `business_id` in the
  database operation itself. A Python-side check after an unscoped fetch is a defect.
- **Never accept a client-supplied `business_id`** as authorization context. It comes from the
  authenticated user's own row.
- **Nonexistent and cross-tenant must be indistinguishable** — both return `404 not_found`, including
  ids referenced inside request bodies. No enumeration, no count leakage.
- **Access tokens carry identity only** (`iss`, `aud`, `sub`, `type`, `jti`, `iat`, `exp`). No role,
  email, or business claim. Role and active state load from PostgreSQL on every protected request.
- **Domain mutation + its required activity-log row commit in ONE transaction**, or neither commits.
- **Never expose `{"detail": ...}`**, stack traces, database errors, tokens, or password hashes in a
  response or a log line.
- **Bookings have no hard delete.** `DELETE /bookings/{id}` is `405 method_not_allowed`.
- **Never edit the ten checksum-protected Phase 0 artifacts** listed in
  `docs/project/phase-0-artifacts.sha256`. Formatters must not touch them either.
- **Any new dotenv filename must be added to the `.env` deny list** in `.claude/settings.json`. That
  list denies Claude's built-in file tools only — it does not cover a Bash subprocess reading the file
  (`cat .env` and equivalents).

## Workflow

### Approval-gated operating mode

Repository and GitHub state transitions — including issue creation, branch and synchronization
operations, progress-state updates, commits, pushes, pull requests, and merges — require
per-operation approval. Present the exact operation separately, wait, and verify its real output
before continuing. Approval may be satisfied either by the operator executing the operation
externally and returning its output or by approving that single tool call. File drafting and edits
are not otherwise state transitions and may proceed after the issue, synchronized `main`, and feature
branch are verified. Never batch multiple state transitions into one approval.

Work the backlog in order. One task = one branch = one PR.

`docs/project/implementation-backlog.md` is the frozen, checksum-protected **plan** — never tick its
checkboxes casually. `docs/project/progress.md` is the living **state**: what is actually done, what
is next. Update `progress.md` in the same PR that completes a task.

1. Read the task entry in `docs/project/implementation-backlog.md`, its `Depends on`, and its
   `Contract coverage`.
2. Read the owning artifact section before writing code. Use plan mode for anything touching more
   than two files or any concurrency, migration, or auth behavior.
3. **Write the failing test first.** Backlog §2 requires tests fail before the implementation and
   pass after. Contract tests are numbered — name them so the number is traceable.
4. Implement the smallest change that passes.
5. Run the checks. Show me the output, do not assert success.
6. Update README, `.env.example`, runbook, or Decision Log in the same commit when behavior,
   setup, limitations, or architecture changed.

Use `/task-start <task-id>` to open a task and `/ship-task` to close it.

### Branches and commits

- Branch naming is owned by `docs/project/git-operating-rules.md` under **Branch and commit naming**;
  follow that rule instead of restating its pattern here.
- Commit: Conventional Commits imperative — `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- One coherent change plus its tests and docs per commit.
- `main` is protected. Never commit or push directly to it. Always branch → PR → merge. Merging a PR,
  deleting its remote branch, and deleting its local branch are three separate approvals — never
  bundle `--delete-branch` into the merge command. Full command sequence and every other Git/GitHub
  mechanical rule: `docs/project/git-operating-rules.md`.
- Never bypass branch protection or disable `enforce_admins` unless I explicitly ask.

### Shell policy pin

`.claude/settings.json` sets `CLAUDE_CODE_USE_POWERSHELL_TOOL: "0"` because the native PowerShell tool
rolls out progressively on Windows and can activate without action. The git guard hook and the
`Bash(git *)` / `Bash(gh *)` permission rules assume a Bash-only tool surface. Lifting this pin
requires moving the hook matchers to `Bash|PowerShell`, adding `PowerShell(...)` equivalents for those
permission rules, and testing both paths — not just flipping the flag.

## Commands

The application scaffold is being built in Phase 1. Until a command exists, say so rather than
guessing an invocation.

```bash
# Phase 0 artifact integrity (works today, from repo root)
sha256sum -c docs/project/phase-0-artifacts.sha256

# Backend — available from P1-02 onward
cd backend && ruff format . && ruff check --fix .   # format + lint
cd backend && mypy app                              # type check
cd backend && pytest                                # full suite
cd backend && pytest -m "not concurrency and not dst"  # fast loop
cd backend && alembic upgrade head && alembic downgrade base && alembic upgrade head

# Environment — available from P1-04 onward
docker compose up -d && docker compose logs -f backend
docker compose down -v   # destroys the dev volume

# Frontend — available from P6-01 onward
cd frontend && npm run dev && npm run lint && npm run typecheck && npm run test
```

Prefer targeted test selection over the full suite while iterating. Run the full suite before a PR.

## Layout

`docs/project/file-structure.md` is the canonical hierarchy — follow it exactly; do not invent
directories. Short version:

- `backend/app/` — `api/v1/endpoints/`, `core/`, `db/`, `middleware/`, `models/`, `repositories/`,
  `schemas/`, `services/`
- `backend/alembic/versions/` — explicit revision ids, `file_template = %%(rev)s_%%(slug)s`
- `backend/tests/` — `contract/`, `integration/`, `unit/`, plus `conftest.py` and `factories.py`
- `frontend/src/features/<domain>/` — feature-sliced; `pages/` is routed composition only
- `docs/` — frozen artifacts; see the authority table above

`backend/pyproject.toml` is the single editable dependency source. `backend/requirements.txt` is a
generated pinned export with pip-compile's native autogenerated header. Regenerate it with
`pip-compile --output-file=requirements.txt pyproject.toml`; never hand-edit it.

## Naming

`kebab-case` folders and docs; `snake_case` Python modules; `PascalCase` classes;
`UPPER_SNAKE_CASE` env vars. Never use `FINAL`, `VERIFIED`, `LATEST`, `NEW`, or `(1)` in a filename.
Versions live in document headers and Git history, not in filenames — the frozen Specification v1.2
and ERD v1.2 are the only exceptions.

## Delegate to keep this context clean

Spawn a subagent instead of reading dozens of files in the main thread:

- `backlog-navigator` — what's next, what it depends on, what it must satisfy (cheap, read-only)
- `contract-auditor` — does this implementation match its contract, clause by clause
- `tenant-isolation-auditor` — find any operation that is not tenant-scoped
- `schema-parity-checker` — DBML vs migrations vs ORM models
- `concurrency-reviewer` — lock order, races, transaction/audit atomicity
- `security-reviewer` — secrets, JWT, hashing, error and log leakage
- `contract-test-author` — write the numbered contract tests
- `docs-sync` — what documentation this change obligates you to update

Before calling a task done, have `contract-auditor` review the diff against the owning contract in a
fresh context. Tell it to report only gaps that affect correctness or a stated requirement.

## Talking to me

I am a solo developer building this to get hired and later to sell. I have ADHD. How you answer
matters as much as what you answer.

- **Lead with the action.** First line is the command, path, or edit. Not context, not a plan.
- **Number multi-step work.** One bounded action per step. Cap lists at five; past that, split into
  "now" and "later" rather than adding items.
- **Restate position every turn** — "Step 3 of 5 done: migration 002 replays clean. Next: ...".
  I cannot hold state between messages, so anything not on screen is gone.
- **Give concrete time estimates.** "About 20 minutes" or "an afternoon", never "some work".
- **End with one action I can start in under two minutes.** Even "open the file" counts.
- **Finish one thing before raising the next.** A second issue is a separate question at the end,
  never a mid-answer tangent.
- **Show what now works**, concretely, in one line. Do not bury a win inside a recap.
- **State errors flatly**: cause, then fix. No "uh oh", no "there seems to be a problem".
- **No filler.** Skip "Great question", "Let me…", "Hope this helps", "Let me know if…". Warmth and a
  real reaction are fine; empty openers and closers are not.

Override these when I ask you to explain or walk me through something — then take the space the topic
needs, with headers so I can skim back. Always stop and confirm before anything destructive. If we
have been stuck three turns, stop iterating on code and name the assumption that might be wrong.

If a backlog task is underspecified, ask before coding — do not fill the gap with a plausible guess.
If you catch a real flaw in the frozen specification, say so plainly; a Decision Log entry is cheaper
than a wrong build.

<!-- Maintainer note: keep this file under 200 lines. Anything path-specific belongs in
     .claude/rules/. Anything procedural belongs in .claude/skills/. -->
