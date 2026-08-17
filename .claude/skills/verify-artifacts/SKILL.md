---
name: verify-artifacts
description: Verify the ten checksum-protected Phase 0 artifacts against the manifest, cross-platform, and diagnose a mismatch.
disable-model-invocation: true
---

# Verify Phase 0 artifact integrity

Run this after changing formatting, line-ending, or pre-commit tooling; after any tool touched a file
under `docs/`; and before any phase tag.

## Verify

From the repository root, on Linux, macOS, or Git Bash:

```bash
sha256sum -c docs/project/phase-0-artifacts.sha256
```

On Windows PowerShell, use the loop in `README.md` § *Phase 0 artifact verification*.

Then confirm the manifest itself:

```bash
sha256sum docs/project/phase-0-artifacts.sha256
```

Expected: `a84e2b1f490bb9ac3e94c806faeb2a5a051a67b6b27a8e5c8410412a942cf5f8`, which is also recorded in
the `phase-0-complete` tag message. Check the tag:

```bash
git tag -v phase-0-complete 2>/dev/null || git show phase-0-complete --no-patch
```

## If a file fails

Do not "fix" it by regenerating the manifest. Diagnose first:

1. `git log --oneline -- <path>` — what changed it, and when.
2. `git diff phase-0-complete -- <path>` — what actually differs.
3. Common causes, in order of likelihood:
   - a formatter or pre-commit whitespace hook that was not excluded per `CONTRIBUTING.md`
   - CRLF/LF conversion — check `.gitattributes` (`* text=auto eol=lf`, `*.pdf binary`, `*.docx binary`)
   - an editor adding or stripping a trailing newline
   - a genuine, intentional edit

For an accidental change: restore the file from the tag and fix the tool that caused it.

```bash
git checkout phase-0-complete -- <path>
```

For an intentional, approved change: recompute the manifest, report the new manifest hash, and record
it so the tag reference can be reconciled. Commit as `docs:`, alone.

## Report

`file | expected | actual | verdict`, then the cause and the remedy. If everything matches, say so in
one line with the manifest hash.
