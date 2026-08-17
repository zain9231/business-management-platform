---
name: ship-task
description: Close a backlog task — verify the definition of done, sync documentation, commit, push, and open the pull request.
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

## 4. Commit

```bash
git status
git diff
git add <specific paths>
git commit
```

Conventional Commits, imperative, one coherent change. Reference the task id in the body:

```
feat: add customer creation endpoint

Implements P4C-03. Covers Customers Contract tests 1, 4, 11, 12.
```

Never `git add .` without reading `git status` first. Never commit a secret, a `.env`, generated
output, or a stale download.

## 5. Pull request

```bash
git push -u origin <branch>
gh pr create --fill
```

Fill the template at `.github/pull_request_template.md` completely: backlog task id, owning contract,
required contract tests, whether a Decision Log entry is needed, and every verification checkbox.

## 6. Merge

Wait for CI. Then:

```bash
gh pr merge --squash --delete-branch
git switch main && git pull --ff-only
```

Never push to `main` directly. Never use `--admin` or disable `enforce_admins` unless I ask
explicitly and say why.

## 7. Progress

Update `docs/project/progress.md` in the same commit as the change:

- move the task into **Completed** with the date, the branch or PR number, and the evidence that
  satisfied its contract coverage — not just a date
- advance the `Next task:` line to the next task in backlog order
- clear it from **In progress**

Do **not** tick checkboxes in `docs/project/implementation-backlog.md`. It is checksum-protected and
stays frozen as the accepted plan; `progress.md` carries the state.
