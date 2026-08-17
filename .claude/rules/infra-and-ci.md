---
paths:
  - ".github/workflows/**"
  - "compose.yaml"
  - "backend/Dockerfile"
  - "frontend/Dockerfile"
  - "backend/pyproject.toml"
  - "backend/requirements.txt"
  - ".env.example"
  - ".pre-commit-config.yaml"
---

# Infrastructure and CI rules

## Dependencies

`backend/pyproject.toml` is the only editable dependency source. `backend/requirements.txt` is a
generated, fully pinned export carrying a `DO NOT EDIT` header; regenerate it whenever dependencies
change and let CI fail on drift. Never hand-edit it and never let the two lists diverge.

Pin everything: Python dependencies, npm dependencies, base images, and GitHub Actions (by SHA where
practical). An unpinned build is not reproducible and the Phase 1 gate requires reproducibility.

## Containers

- Multi-stage build; non-root runtime user; deterministic install; explicit healthcheck.
- **Migrations are an explicit release step**, never a container-startup side effect — multiple
  instances starting at once must not race `alembic upgrade`.
- Development conveniences (hot reload, mounted source, seed data) stay out of the production stage.
- No secrets in `compose.yaml`, image layers, or build args. Source them from the environment.

## CI

The pipeline runs, in order: format check → lint → type check → migration upgrade/downgrade/replay
against real PostgreSQL → unit tests → integration tests. It must fail on migration drift, on a test
failure, and on a committed secret.

Cache dependency downloads. Never cache generated application state or a database volume.

## Configuration

Every setting is typed and validated at startup. Production fails fast on a missing or unsafe value —
no development fallback for a JWT secret, database URL, issuer, audience, or CORS origin list.

`.env.example` contains placeholders only. If you add a setting, add it there in the same commit and
document it in the README.

## Pre-commit

Whitespace and formatting hooks must exclude the seven checksum-protected Markdown files using the
regex in `CONTRIBUTING.md`. Set `check-added-large-files --maxkb=2048` so the accepted 1,024,807-byte
ERD PDF passes while unexpected large additions are still blocked. Include a secret scanner.

After changing any formatting, line-ending, or pre-commit tooling, re-verify the Phase 0 manifest
from a clean checkout.
