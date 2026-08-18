# Backend

FastAPI application package. Pinned dependency source is `pyproject.toml`; `requirements.txt` is a
generated export and must never be hand-edited.

`httpx2` (not `httpx`) is the pinned test-client dependency: it is what `starlette.testclient`
actually imports when present (`import httpx2 as httpx`, tried before the deprecated `httpx` path).
See PR #11 for the supply-chain verification behind that pin.

## Setup

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"     # Windows; use .venv/bin/pip on Linux/macOS
```

## Start the backend

```bash
.venv/Scripts/uvicorn app.main:app --reload     # Windows; use .venv/bin/uvicorn on Linux/macOS
```

`GET /health/live` returns `{"status": "live"}` once the process is up.

## Tests

```bash
.venv/Scripts/pytest     # Windows; use .venv/bin/pytest on Linux/macOS
```

Database configuration, Docker Compose, linting, type checking, migrations, and the full test
harness are added in later Phase 1 tasks; see `docs/project/implementation-backlog.md`.
