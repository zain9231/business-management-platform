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

## Configuration

`Settings` (`app/core/config.py`) reads process environment variables only — it does not
automatically load `.env`. Populate every required variable before starting the backend.

| Variable | Required / default | Accepted values |
|---|---|---|
| `DATABASE_URL` | required | `postgresql+psycopg://` connection URL |
| `JWT_SECRET` | required | at least 32 UTF-8 bytes; rejects the ten placeholder markers and the `.env.example` sentinel, case-insensitively |
| `JWT_ISSUER` | required | non-empty string, surrounding whitespace trimmed |
| `JWT_AUDIENCE` | required | non-empty string, surrounding whitespace trimmed |
| `CORS_ALLOWED_ORIGINS` | required | JSON array of unique, explicit `http`/`https` origins — no wildcard host, userinfo, path, query, fragment, backslash, or malformed port |
| `ENVIRONMENT` | required | `development`, `test`, or `production` |
| `LOG_LEVEL` | default `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (case-insensitive) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | default `15` | positive integer |
| `REFRESH_TOKEN_EXPIRE_DAYS` | default `14` | positive integer |

If the required variables are already exported in the shell (CI, a container, a configured
launcher), start the backend directly:

```bash
.venv/Scripts/uvicorn app.main:create_app --factory --reload     # Windows; use .venv/bin/uvicorn on Linux/macOS
```

Otherwise, copy the root example, edit the secret, and load the edited `.env` into the child
process only — do not use `set -a; source ../.env; set +a`, since shell sourcing strips the quotes
`CORS_ALLOWED_ORIGINS` needs for its JSON array:

PowerShell:

```powershell
Copy-Item ..\.env.example ..\.env
# Edit ..\.env and replace JWT_SECRET
.venv/Scripts/python -m dotenv -f ../.env run -- ./.venv/Scripts/uvicorn app.main:create_app --factory --reload
```

Linux/macOS/Git Bash:

```bash
cp ../.env.example ../.env
# Edit ../.env and replace JWT_SECRET
.venv/bin/python -m dotenv -f ../.env run -- ./.venv/bin/uvicorn app.main:create_app --factory --reload
```

`GET /health/live` returns `{"status": "live"}` once the process is up.

## Tests

```bash
.venv/Scripts/pytest     # Windows; use .venv/bin/pytest on Linux/macOS
```

Database configuration, Docker Compose, linting, type checking, migrations, and the full test
harness are added in later Phase 1 tasks; see `docs/project/implementation-backlog.md`.
