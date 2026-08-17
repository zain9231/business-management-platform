---
name: decision-log
description: Draft and record a Decision Log entry in the master specification when a frozen decision must change, and reconcile the Phase 0 checksum manifest afterwards.
disable-model-invocation: true
---

# Decision Log entry

The Decision Log inside `docs/project/master-specification-v1.2.docx` is the highest authority for
post-freeze decisions. It is the only sanctioned way to change frozen scope or architecture.

## When this is required

- Two authoritative artifacts genuinely contradict each other.
- A frozen requirement is unimplementable as written, or is wrong.
- Frozen scope or architecture must change.
- A new endpoint inventory or contract is being accepted (P4U-01, P7-01, P8-01, P9-01).
- A conventions exception is needed — for example the P8-01 amendment to the customer/service
  `custom_fields` write freeze.

**Not** required for an implementation detail the artifacts already delegate, or for anything you can
resolve by reading the owning artifact more carefully. Try that first.

## Draft the entry

Produce this in the conversation for my approval before touching the file:

1. **Date** and **decision id**, following the numbering already in the log.
2. **Context** — what was being implemented and what surfaced the problem, in two or three sentences.
3. **The conflict or gap**, quoting both artifacts verbatim with their file paths.
4. **Options considered**, each with its consequence. At least two.
5. **Decision** — one unambiguous sentence stating the new rule.
6. **Scope of the override** — exactly which artifact text this supersedes, quoted.
7. **Consequences** — which contracts, tests, migrations, or backlog tasks now change.
8. **Status** — accepted, and by whom.

Write it in the existing register: plain declarative sentences, no marketing language, no emoji.

## After approval

1. Append the entry to the Decision Log in the `.docx`. Do not restructure the document.
2. Update the artifact that the decision overrides, referencing the decision id inline.
3. Recompute `docs/project/phase-0-artifacts.sha256` — the spec is checksum-protected.
4. Report the manifest's new SHA-256 so the tag record can be reconciled.
5. Commit alone, as `docs:`, never bundled with implementation.

If a decision changes an accepted contract, the contract's numbered test list must be updated in the
same change. A decision that silently invalidates a passing test is worse than no decision.
