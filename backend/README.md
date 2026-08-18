# Backend

FastAPI application package. Pinned dependency source is `pyproject.toml`; `requirements.txt` is a
generated export and must never be hand-edited.

## Setup

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"     # Windows; use .venv/bin/pip on Linux/macOS
```

## Start the backend

```bash
.venv/Scripts/uvicorn app.main:app --reload
```

`GET /health/live` returns `{"status": "live"}` once the process is up.

## Tests

```bash
.venv/Scripts/pytest
```

Database configuration, Docker Compose, linting, type checking, migrations, and the full test
harness are added in later Phase 1 tasks; see `docs/project/implementation-backlog.md`.
