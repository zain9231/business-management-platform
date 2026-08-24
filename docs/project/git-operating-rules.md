# Git and GitHub Operating Rules

Mechanical, command-level Git and GitHub rules for this repository. Every state transition still
requires its own approval under the approval-gated operating mode; that mode is stated once, in
`CLAUDE.md`, and is not repeated here.

This file is the single owner of the rules below. Do not restate them elsewhere — reference this
file instead.

## Branch and commit naming

Historical provenance marked "consolidated from" refers to the source snapshot immediately before
the consolidation commit: `9d9c76caa3b9eedfb10d540442c3b16699832edd`. Section headings and named
symbols below identify material as it stood in that snapshot; resolve them with
`git show 9d9c76caa3b9eedfb10d540442c3b16699832edd:<path>`, not against the current file.

| Rule | Provenance |
|---|---|
| Branch: `<type>/<issue-or-task-id>-<short-description>`, e.g. `feat/p3-01-jwt-issuance` | consolidated from `CLAUDE.md` **Branches and commits**, `CONTRIBUTING.md` **Branch workflow**, and `.claude/skills/task-start/SKILL.md` **Create the feature branch from synchronized main** |
| `<type>` is `feat`, `fix`, `test`, `docs`, or `chore` | consolidated from `.claude/skills/task-start/SKILL.md` **Create the feature branch from synchronized main** |
| Commit messages: Conventional Commits, imperative mood, one coherent change per commit | consolidated from `CLAUDE.md` **Branches and commits**, `CONTRIBUTING.md` **Commit messages**, and `.claude/skills/ship-task/SKILL.md` **Commit** |
| `main` is protected; never commit or push to it directly | consolidated from `CLAUDE.md` **Branches and commits** and `CONTRIBUTING.md` **Protected main workflow**; mechanically enforced by `.claude/hooks/guard_git.py`'s direct-push matcher and `main()` branch check |

## The canonical merge and branch-deletion sequence

Five separate approvals. Never bundle any two of these into one command or one approval — a bundled
command was the defect that produced this file.

a. `gh pr merge <number> --squash` — no `--delete-branch`.
b. Sync local `main` (`git switch main`, `git pull --ff-only`).
c. `gh api -X DELETE 'repos/{owner}/{repo}/git/refs/heads/<branch>'` — delete the remote branch.
   The single quotes are shell syntax; `{owner}` and `{repo}` remain literal placeholder syntax that
   `gh api` substitutes from the current repository. Do not hand-substitute them.
d. `git branch -D <branch>` — delete the local branch.
e. `git fetch --prune` — clear the stale remote-tracking ref left by step c.

| Step | Provenance |
|---|---|
| a. Merge without `--delete-branch` | consolidated and corrected from `CLAUDE.md` **Branches and commits**, `CONTRIBUTING.md` **Protected main workflow**, `.claude/skills/ship-task/SKILL.md` **Merge**, and `.claude/hooks/guard_git.py`'s `PR_WORKFLOW` and remote-ref-deletion rule — all five previously stated the bundled `gh pr merge --squash --delete-branch`; that form is removed here |
| b. Sync local main | consolidated from `.claude/skills/ship-task/SKILL.md` **Sync local main** and `.claude/skills/task-start/SKILL.md` **Sync main and confirm a clean working tree** |
| c. Remote deletion via the canonical step-c command | newly codified from operating experience — audit of `.claude/hooks/guard_git.py` found this is the only branch-deletion form that is order-independent and unconditionally unblocked. `git push origin --delete <branch>` is always blocked; `git push origin :<branch>` is blocked whenever local HEAD is `main`, which step b puts it on |
| d. `git branch -D <branch>` | newly codified from operating experience — no local-branch-deletion rule existed anywhere in the repository before this file. `-d` fails because the branch tip is not an ancestor of `main` after a squash merge; `-D` is required |
| e. `git fetch --prune` | newly codified from operating experience — four stale remote-tracking refs accumulated before they were pruned as a separate housekeeping item |

## Pushing and opening the pull request

- Push explicitly before creating the PR: `git push -u origin <branch>`. `gh pr create` will push an
  unpushed branch itself if this step is skipped, which bundles two state transitions into one
  approval. Consolidated from `CONTRIBUTING.md` **Protected main workflow** and
  `.claude/skills/ship-task/SKILL.md` **Push and open the pull request**.
- `gh pr create --title "<title>" --body-file <path>`. Never `--fill`. Consolidated from
  `.claude/skills/ship-task/SKILL.md` **Push and open the pull request**.
- The PR title is byte-identical to the commit subject. Newly codified from operating experience.
- The merge body is derived from the commit, not typed fresh. Newly codified from operating
  experience.

## Body files (commit, PR, merge)

Any file passed as a commit, PR, or merge body:

- lives outside the worktree;
- is verified (read back) before use;
- is deleted whether the command it fed succeeded or failed;
- is UTF-8, LF line endings only, no CR bytes, no BOM.

Consolidated from `.claude/skills/ship-task/SKILL.md` **Push and open the pull request** (PR body
only — extended here to commit and merge bodies). The encoding constraints are newly codified from
operating experience; no existing file states them.

## Commit message mechanics

- Never pass a multi-line message with `-m`. Use an editor or a body file. Newly codified from
  operating experience — `.claude/skills/ship-task/SKILL.md` **Commit** already shows `git commit`
  without `-m` but never states the rule.
- A blank line separates the commit subject from the body. Prove `%b` is non-empty after committing
  (`git log -1 --format=%b`). Newly codified from operating experience.

## Known guard gap

`.claude/hooks/guard_git.py` blocks `git push origin --delete <branch>` always and blocks
`git push origin :<branch>` only when local HEAD is `main`. It does not block
`gh pr merge --delete-branch`, so its branch-deletion coverage remains inverted relative to the
sequence in this file: it blocks a form nobody needs here and lets through the bundled merge form
this file forbids. The required step-c form remains intentionally unblocked.

The guard separately inspects Bash command text for co-occurring `enforce_admins` and `DELETE` tokens.
That branch-protection rule is covered by the root hook tests and does not close this branch-deletion
gap. The root guard-test surface now exists, satisfying the test-surface part of the original
deferral; changing branch-deletion matching remains deferred until after P1-07. Until then, if the
guard ever blocks a form this file requires, stop and report it — do not substitute an unblocked form
to get around the block. A `PreToolUse` denial happens before permission rules are evaluated; no
document overrides it.
