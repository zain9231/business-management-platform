---
paths:
  - ".claude/*"
  - ".claude/**/*"
---

# Maintaining the `.claude/` tree

Parts of this tree restate rules it does not own, and a restatement can drift from its owner while
still reading as authoritative. Before changing a file here, determine whether it restates a rule
from the authority table in `CLAUDE.md`. If it does, check the restatement against the owning
artifact; when the two disagree the artifact wins and the restatement is corrected, never the
reverse.

When hook configuration changes, `.claude/README.md`'s inventory is updated in the same change to
match `.claude/settings.json`. `settings.json` is the configuration; the README only describes it,
and a description that is not updated with what it describes is a defect. `tests/hooks/` holds the
tests that enforce this.
