---
name: task-start
description: Open a backlog task correctly — verify live status, sync main, create the issue and branch, read the owning artifacts, and produce a plan before any code is written.
argument-hint: "<task-id> e.g. P2-03"
disable-model-invocation: true
---

# Start backlog task $ARGUMENTS

Do not write implementation code during this skill. The output is a captured issue number, a branch,
and a plan.

## Live-status rule

`docs/project/progress.md` is authoritative for the current task. GitHub issues are authoritative for
in-flight work. `docs/project/implementation-backlog.md` supplies scope, sequence, dependencies,
acceptance criteria, and gates; its checkbox state is never a status source. If `progress.md` is
unreadable or absent, has a missing or duplicate `Next task:` line, has a task identifier that fails
the expected format, or names a task identifier not found in the backlog, stop: cannot determine
current task. Do not infer from backlog checkboxes.

## 1. Locate the task

Read `docs/project/progress.md` for the current state, then use the `backlog-navigator` subagent for
`$ARGUMENTS`. Confirm:

- every `Depends on` task is recorded complete in `progress.md` — if not, **stop** and tell me which
  one blocks it
- the task matches the `Next task:` line in `progress.md`; if I am skipping ahead, say so and ask

Use backlog checklist text for scope and acceptance criteria only, never as completion evidence.

## 2. Read the authorities

Read, in full, the sections that actually govern this task:

- the owning contract in `docs/api/contracts/`, if the task names contract coverage
- `docs/api/shared-api-conventions.md` for the cross-cutting behavior it inherits
- the relevant table blocks in `docs/architecture/erd/source/business-management-platform-erd-v1.2.dbml`
- `docs/project/file-structure.md` for exactly where the new files belong

Never open the ERD PDF. If two artifacts disagree, stop and report it — that is a Decision Log matter.

## 3. Sync main and confirm a clean working tree

```bash
git status --short
```

If the status is clean, present and verify these state transitions separately:

```bash
git switch main
```

```bash
git pull --ff-only
```

Then inspect again:

```bash
git status --short
```

Stop if either status check reports changes. Confirm local `main`, `origin/main`, and `HEAD` identify
the synchronized commit before continuing.

## 4. Create exactly one GitHub issue

Check all issue states for an existing issue for this task. If exactly one exists, capture and verify
its number rather than creating a duplicate. If more than one exists, stop and report them. If none
exists, draft a focused issue body from the task authorities, review it, then present this command:

```bash
gh issue create --title "<task-id>: <task-title>" --body-file <reviewed-issue-body-path>
```

Capture the real issue number from the returned URL and verify the issue before continuing. The issue
must exist before any feature-branch creation command is presented.

## 5. Create the feature branch from synchronized main

```bash
git switch -c <type>/<task-id-lowercase>-<short-description>
```

`<type>` is `feat`, `fix`, `test`, `docs`, or `chore`. Example:
`feat/p2-03-customers-staff-services-migration`.

Never work on `main`.

For repository and GitHub state transitions, present one command at a time and wait for per-operation
approval. Approval may be the operator executing the command externally and returning its output, or
approval of that single tool call. Verify the real output before presenting the next transition.

## 6. Write the plan

Produce, in the conversation:

1. **Files to create or change**, at their exact canonical paths from `file-structure.md`.
2. **The failing tests you will write first**, each named and mapped to its contract test number.
3. **The authority citation for every non-obvious decision** — quote the contract or DBML line.
4. **Open questions.** Anything the artifacts do not answer. Do not fill a gap with a guess; ask me.
5. **The verification command** that will prove the task is done.
6. **The definition-of-done items** from backlog §2 that apply, and which are not applicable and why.

## 7. Stop

Wait for me to approve the plan. Then write the failing tests first, show them failing, and only
then implement.

If the task touches concurrency, migrations, authentication, or more than two files, do steps 2–4 in
plan mode.
