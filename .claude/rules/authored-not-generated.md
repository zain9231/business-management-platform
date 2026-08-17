---
paths:
  - "**/*.md"
  - "backend/**/*.py"
  - "frontend/src/**/*.{ts,tsx}"
---

# Write like the person whose name is on the repository

This repository is portfolio evidence. A reviewer decides whether the engineering is credible partly
from how the prose and the code read. Machine-default output has recognisable tells; this file lists
them so you avoid them.

**Scope note:** the "Talking to me" rules in `CLAUDE.md` govern how you address me in chat — lead with
the action, number the steps, cap lists at five. Those do **not** apply to committed files. A README
is not a numbered checklist and a docstring is not a status update.

## The house voice

The accepted Phase 0 artifacts define it. Match them:

- **Plain declarative sentences.** "Phase 0 is complete." Not "Phase 0 has now been successfully
  completed, marking an important milestone."
- **Say must, never, always** when you mean them. Do not hedge a real rule into "should generally".
- **Tables for enumerable rules**, prose for reasoning. Not bullet lists of everything.
- **Precise numbers**: "the accepted 1,024,807-byte ERD PDF", not "the large PDF".
- **Give the reason when a rule is non-obvious**, in one clause. "Those are document status values,
  not filename identity."
- **State the negative space.** What is excluded, what is not authoritative, what is deferred. The
  existing docs do this constantly and it is why they read as considered rather than generated.

## Prose tells to avoid

- Marketing adjectives with no measurement behind them: powerful, seamless, robust, comprehensive,
  cutting-edge, game-changing, enterprise-grade, blazing-fast.
- The contrast cliché: "It's not just X, it's Y." "This isn't about X — it's about Y."
- Filler connectives: additionally, furthermore, moreover, it's worth noting that, in today's
  landscape, let's dive in.
- A closing paragraph that summarises what the document just said, or promises a benefit: "By
  following these steps, you'll be able to…".
- Restating the heading as the first sentence beneath it.
- Emoji, exclamation marks, and bold sprinkled mid-sentence for emphasis.
- Uniform rhythm: every section the same length, every list exactly three items, every sentence the
  same shape. Real writing is uneven because real emphasis is uneven.
- Hedging adverbs that carry no information: perhaps, might possibly, could potentially.

## Code tells to avoid

- Comments that restate the code. `# increment the counter`. Comment the *why*, or not at all.
- Step narration: `# Step 1: validate input`, `# Step 2: query the database`.
- Docstrings that paraphrase the signature. If the name and types say it, the docstring is noise.
- Defensive code for impossible states: `if x is not None` on a value that is never None; `try/except`
  around something that cannot raise; a bare `except Exception: pass`.
- Abstraction with one caller. A factory for two tables. A wrapper that only forwards.
- `Any` used to make a type checker stop complaining.
- Leftover `print()`, `TODO: implement`, or placeholder branches.
- Names that describe the type instead of the meaning: `customer_data_dict`, `result_object`.
- Tests that only cover the happy path, or that assert on human-readable message text instead of
  status code and error code.

## When you catch yourself

If a paragraph reads smoothly but you cannot point at what it commits to, delete it. If a comment
would still be true after the function is rewritten, delete it. Length is not evidence of effort, and
a reviewer reads absence of padding as confidence.
