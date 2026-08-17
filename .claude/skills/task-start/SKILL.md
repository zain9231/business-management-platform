---
name: task-start
description: Open a backlog task correctly — read the owning artifacts, create the branch, and produce a plan before any code is written.
argument-hint: "<task-id> e.g. P2-03"
disable-model-invocation: true
---

# Start backlog task $ARGUMENTS

Do not write implementation code during this skill. The output is a plan and a branch.

## 1. Locate the task

Read `docs/project/progress.md` for the current state, then use the `backlog-navigator` subagent for
`$ARGUMENTS`. Confirm:

- every `Depends on` task is recorded complete in `progress.md` — if not, **stop** and tell me which
  one blocks it
- the task matches the `Next task:` line in `progress.md`; if I am skipping ahead, say so and ask

## 2. Read the authorities

Read, in full, the sections that actually govern this task:

- the owning contract in `docs/api/contracts/`, if the task names contract coverage
- `docs/api/shared-api-conventions.md` for the cross-cutting behavior it inherits
- the relevant table blocks in `docs/architecture/erd/source/business-management-platform-erd-v1.2.dbml`
- `docs/project/file-structure.md` for exactly where the new files belong

Never open the ERD PDF. If two artifacts disagree, stop and report it — that is a Decision Log matter.

## 3. Create the branch

```bash
git switch main
git pull --ff-only
git switch -c <type>/<task-id-lowercase>-<short-description>
```

`<type>` is `feat`, `fix`, `test`, `docs`, or `chore`. Example: `feat/p2-03-customers-staff-services-migration`.

Never work on `main`.

## 4. Write the plan

Produce, in the conversation:

1. **Files to create or change**, at their exact canonical paths from `file-structure.md`.
2. **The failing tests you will write first**, each named and mapped to its contract test number.
3. **The authority citation for every non-obvious decision** — quote the contract or DBML line.
4. **Open questions.** Anything the artifacts do not answer. Do not fill a gap with a guess; ask me.
5. **The verification command** that will prove the task is done.
6. **The definition-of-done items** from backlog §2 that apply, and which are not applicable and why.

## 5. Stop

Wait for me to approve the plan. Then write the failing tests first, show them failing, and only
then implement.

If the task touches concurrency, migrations, authentication, or more than two files, do steps 2–4 in
plan mode.
