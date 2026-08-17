---
name: ship-task
description: Close a backlog task — verify the definition of done, update progress, commit, push, open the pull request, merge, and resync main.
argument-hint: "<task-id> e.g. P2-03"
disable-model-invocation: true
---

# Ship backlog task $ARGUMENTS

## 1. Definition of done — backlog §2

Check each, with evidence, and mark any that does not apply with a reason:

- [ ] Formatted, linted, type-checked, and reviewed against the authoritative artifact
- [ ] Success, failure, authorization, tenant-isolation, and transaction behavior tested
- [ ] Tests failed before the implementation and pass after
- [ ] No secret, token, tenant data, stack trace, or database detail leaks through a log or response
- [ ] Database changes verified with upgrade, clean replay, and downgrade
- [ ] Shared error envelope, strict-input behavior, and deterministic responses retained
- [ ] Documentation updated in the same commit where setup, behavior, limitations, or architecture changed
- [ ] Branch is mergeable without relying on uncommitted local state

Run the checks and paste the real output:

```bash
cd backend && ruff format --check . && ruff check . && mypy app && pytest
```

## 2. Adversarial review

Run `contract-auditor` on the diff against the owning contract, in fresh context. Tell it to report
only gaps affecting correctness or a stated requirement. Fix real gaps; ignore style preferences.

## 3. Documentation

Run the `docs-sync` subagent. Apply the unprotected edits. For any checksum-protected file, show me
the proposed diff and **stop** — I approve it and the manifest recompute separately.

## 4. Progress

Update `docs/project/progress.md` on the feature branch so the change is included in this PR:

- move the task into **Completed** with the date, the branch or PR number, and the evidence that
  satisfied its contract coverage — not just a date
- advance the `Next task:` line only to the next task in backlog order
- clear it from **In progress**

Show the exact progress edit and wait for per-operation approval before applying it.

The progress rule is **in the same PR**, not in the same commit. A branch name is sufficient before
the PR exists. If the progress record must include the PR number, make a follow-up commit on the
feature branch before merge. Do **not** tick checkboxes in
`docs/project/implementation-backlog.md`; it is checksum-protected and stays frozen as the accepted
plan.

## 5. Commit

```bash
git status
git diff
```

Then present and verify each state transition separately:

```bash
git add <specific paths>
```

```bash
git commit
```

Conventional Commits, imperative, one coherent change. Reference the task id in the body:

```
feat: add customer creation endpoint

Implements P4C-03. Covers Customers Contract tests 1, 4, 11, 12.
```

Never `git add .` without reading `git status` first. Never commit a secret, a `.env`, generated
output, or a stale download.

## 6. Push and open the pull request

```bash
git push -u origin <branch>
```

Use the captured issue number from `task-start`. Then:

1. Copy the current `.github/pull_request_template.md` to a temporary file outside the repository.
2. Fill in and review that copy completely: the real `Closes #N` issue number, backlog task id,
   owning contract, required contract tests, Decision Log status, changes, and every verification
   checkbox.
3. Present this command with a focused title and the reviewed temporary path:

   ```bash
   gh pr create --title "<focused title>" --body-file <temporary-path-outside-repository>
   ```

4. Delete the temporary file whether PR creation succeeds or fails.

The submitted body must be derived from the repository template and contain `Closes #N` with the
real captured number. `--body-file` makes the exact submitted body reviewable before the PR exists.
Do not use `--fill`, and do not create a second template.

## 7. Merge

Wait for CI. Then:

```bash
gh pr merge <number> --squash --delete-branch
```

Never push to `main` directly. Never use `--admin` or disable `enforce_admins` unless I ask
explicitly and say why.

## 8. Sync local main

After the merge is verified:

```bash
git switch main
```

```bash
git pull --ff-only
```

For repository and GitHub state transitions — synchronization, progress updates, commits, pushes, PR
creation, merges, and post-merge synchronization — present one operation at a time and wait for
per-operation approval. Approval may be the operator executing it externally and returning its
output, or approval of that single tool call. Verify the real output before presenting the next
transition. Squash-merge only after explicit approval.
