# Requirements Sources and Scoped Authority

**Phase 0 baseline:** accepted 2026-08-16

Artifact authority is scoped rather than expressed as one flat ranking:

- Accepted Decision Log entries inside `master-specification-v1.2.docx` resolve post-freeze decisions and override contradictory earlier specification text.
- `../api/shared-api-conventions.md` is authoritative for shared, cross-cutting API behavior.
- Each finalized file in `../api/contracts/` is authoritative for that endpoint's fields, permissions, filters, transitions, and endpoint-specific behavior.
- `../architecture/erd/source/business-management-platform-erd-v1.2.dbml` is authoritative for schema details, constraints, indexes, checks, relationships, deletion rules, and schema notes.
- `master-specification-v1.2.docx` remains authoritative for frozen product scope and requirements not delegated to another artifact.
- `../architecture/erd/exports/business-management-platform-erd-v1.2.pdf` is a viewing export only and never overrides the DBML.

## Conflict protocol

Do not resolve a conflict by mechanically choosing a supposedly higher-ranked document. Stop implementation and identify which artifact owns the disputed subject. Any exception must be explicit and justified in the owning artifact. A material architectural or frozen-scope change must also be recorded in the master specification's Decision Log.

Generated OpenAPI documentation and rendered diagrams must match the approved sources but never replace them.

## Canonical files

- `master-specification-v1.2.docx`
- `implementation-backlog.md`
- `../api/shared-api-conventions.md`
- `../api/contracts/authentication-api-contract.md`
- `../api/contracts/customers-api-contract.md`
- `../api/contracts/staff-api-contract.md`
- `../api/contracts/services-api-contract.md`
- `../api/contracts/bookings-api-contract.md`
- `../architecture/erd/source/business-management-platform-erd-v1.2.dbml`
- `../architecture/erd/exports/business-management-platform-erd-v1.2.pdf`

Revision numbers for conventions and endpoint contracts are kept in their document headers and Git history. The frozen Specification v1.2 and ERD v1.2 retain version numbers in their filenames because those versions are part of the artifacts' identities.
