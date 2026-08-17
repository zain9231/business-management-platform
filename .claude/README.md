# Claude Code configuration

This directory configures how Claude Code works on this repository. It is checked in deliberately:
the rules it encodes are the same ones in `CONTRIBUTING.md` and `docs/project/requirements-sources.md`,
just in a form a coding agent applies automatically.

## What is here

| Path | Loads | Purpose |
|---|---|---|
| `../CLAUDE.md` | every session, in full | authority table, non-negotiables, workflow, commands |
| `rules/*.md` | when a matching file is opened | path-scoped conventions, kept out of context otherwise |
| `agents/*.md` | on delegation | specialist reviewers running in isolated context |
| `skills/*/SKILL.md` | on `/name` invocation | the repeatable rituals: task start, gates, shipping |
| `settings.json` | every session | permissions and hooks, shared with any collaborator |
| `settings.local.json` | every session | your machine only, gitignored |
| `hooks/*.py` | on lifecycle events | deterministic guards that do not depend on Claude's judgment |

The split matters. `CLAUDE.md` is loaded in full on every request, so it stays under 200 lines and
holds only what would cause a mistake if missing. Everything path-specific is a rule; everything
procedural is a skill; everything that must happen without exception is a hook.

## Skills

Invoke with a slash command. All of these are `disable-model-invocation: true` — they have side
effects, so only you trigger them, and they cost zero context until you do.

| Command | What it does |
|---|---|
| `/task-start P2-03` | reads the backlog entry and owning artifacts, branches, produces a plan — no code |
| `/new-migration 002 create_customers...` | DBML-first migration with upgrade/downgrade/replay proof |
| `/contract-gate customers` | full numbered suite, conventions checklist, adversarial review, OpenAPI |
| `/phase-checkpoint 2` | phase exit gate, full regression, tag |
| `/ship-task P2-03` | definition of done, docs sync, commit, PR, squash merge |
| `/decision-log` | draft a Decision Log entry and reconcile the checksum manifest |
| `/verify-artifacts` | check the ten Phase 0 artifacts against the manifest, diagnose a mismatch |

Three more skills are reference material Claude loads on its own when relevant:
`api-conventions`, `tenant-scoping`, `booking-engine-rules`. **They are navigation aids, not
authorities** — each one points at the artifact that actually owns the rule. That is deliberate:
`docs/project/requirements-sources.md` exists to prevent a second copy of a rule.

## Subagents

Ask for them by name: *"use the tenant-isolation-auditor on the customers repository"*.

`backlog-navigator` (haiku, cheap) · `contract-auditor` · `tenant-isolation-auditor` ·
`schema-parity-checker` · `concurrency-reviewer` · `security-reviewer` (all opus — deep, slower,
worth it at a gate) · `contract-test-author` · `docs-sync` (sonnet).

They run in isolated context and report a summary, so a sweep that reads forty files costs your main
conversation a paragraph. Use one for any review before a gate.

## Hooks

Written in Python so they behave the same in PowerShell, Git Bash, and WSL, and need no `jq`.
Every hook fails open — if Python is missing or a script errors, the session continues.

| Event | Script | Effect |
|---|---|---|
| `SessionStart` | `session_context.py` | prints branch, dirty-file count, last commit, next unchecked backlog task |
| `PreToolUse` (edits) | `guard_protected_paths.py` | blocks writes to the ten checksum-protected artifacts, `.env`, keys |
| `PreToolUse` (Bash) | `guard_git.py` | blocks commits on `main`, direct pushes to `main`, force pushes, `enforce_admins` bypass, history rewrites |
| `PostToolUse` (edits) | `format_after_edit.py` | runs Ruff, or Prettier/ESLint, on the edited file — silent no-op until those tools exist |

**On Linux or WSL**, change `python` to `python3` in the four `command` entries in `settings.json`.
On Windows the launcher is `python`, which is what is configured.

Test a hook by hand:

```bash
echo '{"tool_input":{"file_path":"docs/api/shared-api-conventions.md"},"cwd":"."}' | python .claude/hooks/guard_protected_paths.py
```

A `permissionDecision: "deny"` payload means it is working.

## Maintaining this

Treat it like code. The triggers for changing it:

- Claude gets the same convention wrong twice → add one line to `CLAUDE.md`, or a rule if it is
  path-specific.
- You type the same multi-step instruction a third time → make it a skill.
- Something must happen every time regardless of judgment → make it a hook, not an instruction.
- `CLAUDE.md` passes 200 lines → move something into `rules/` or `skills/`. A bloated `CLAUDE.md`
  causes Claude to ignore the rules that matter, which is worse than not having them.

Prune as aggressively as you add. Run `/context` to confirm what actually loaded, and `/doctor` for a
health check on the configuration.

## Not configured here, on purpose

No `Stop` hook gating on the test suite — it is genuinely useful for unattended runs but noisy while
iterating, and the backend suite does not exist yet. A ready-to-paste block is in
`settings.local.json.example`, to enable from Phase 2 onward.

No MCP servers. Claude Code reaches GitHub through the `gh` CLI, which is more context-efficient than
an MCP equivalent. Add a Postgres MCP server later only if schema inspection during Phase 5 debugging
turns out to be worth the tool-schema overhead.
