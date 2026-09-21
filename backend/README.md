# Backend

FastAPI application package. `pyproject.toml` is the only editable dependency source.
`requirements.txt` is the runtime lock, and `requirements-dev.txt` contains runtime and development
dependencies. Both generated locks are hash checked and must never be hand-edited.

`httpx2` (not `httpx`) is the pinned test-client dependency: it is what `starlette.testclient`
actually imports when present (`import httpx2 as httpx`, tried before the deprecated `httpx` path).
See PR #11 for the supply-chain verification behind that pin.

## Setup

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"     # Windows; use .venv/bin/pip on Linux/macOS
```

The generated locks target the pinned Linux/AMD64 Python 3.13.15 environment. `requirements.txt` is
the container/deployment lock; `requirements-dev.txt` adds test, quality, and CI tooling. They include
Linux-only dependencies such as `uvloop` and omit Windows-only transitive packages, so native Windows
development must use the editable `pyproject.toml` installation above. CI installs the development
lock with `python -m pip install --require-hashes --requirement requirements-dev.txt`; the runtime
container installs `requirements.txt` with the same hash enforcement.

Regenerate both locks only inside the pinned Linux/AMD64 image declared by `PYTHON_IMAGE` in
`Dockerfile`, with `pip-tools==7.6.1`. Do not run these commands with native Windows Python:

```bash
pip-compile --allow-unsafe --generate-hashes --output-file=requirements.txt pyproject.toml
pip-compile --allow-unsafe --extra dev --generate-hashes \
  --output-file=requirements-dev.txt pyproject.toml
```

Activate this environment before running the repository-root quality and Git-hook setup commands
in [the main README](../README.md#quality-checks): `.venv\Scripts\Activate.ps1` in PowerShell or
`source .venv/bin/activate` on Linux/macOS. Git Bash on Windows uses `source .venv/Scripts/activate`.

## Configuration

`Settings` (`app/core/config.py`) reads process environment variables only — it does not
automatically load `.env`. Populate every required variable before starting the backend.

Use `load_settings()` to construct application settings. It converts validation and source-parsing
failures into `ConfigurationError`, whose text, `errors()`, and `json()` contain only safe locations
and reasons, with no original exception chain. Direct `Settings()` construction is reserved for the
configuration module and tests: its structured Pydantic errors still contain raw input. Keep validator
messages free of input values, and never log settings objects.

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
launcher), start the backend directly. Keep 8000 as the ordinary default while allowing the caller
to provide a run-owned `BACKEND_PORT`.

PowerShell:

```powershell
if (-not $env:BACKEND_PORT) { $env:BACKEND_PORT = "8000" }
.venv/Scripts/uvicorn app.main:create_app --factory --reload --port $env:BACKEND_PORT
```

Linux or macOS:

```bash
export BACKEND_PORT="${BACKEND_PORT:-8000}"
.venv/bin/uvicorn app.main:create_app --factory --reload --port "$BACKEND_PORT"
```

Git Bash on Windows:

```bash
export BACKEND_PORT="${BACKEND_PORT:-8000}"
.venv/Scripts/uvicorn app.main:create_app --factory --reload --port "$BACKEND_PORT"
```

Otherwise, copy the root example, edit the secret, and load the edited `.env` into the child
process only — do not use `set -a; source ../.env; set +a`, since shell sourcing strips the quotes
`CORS_ALLOWED_ORIGINS` needs for its JSON array:

PowerShell:

```powershell
Copy-Item ..\.env.example ..\.env
# Edit ..\.env and replace JWT_SECRET
if (-not $env:BACKEND_PORT) { $env:BACKEND_PORT = "8000" }
.venv/Scripts/python -m dotenv -f ../.env run -- ./.venv/Scripts/uvicorn app.main:create_app --factory --reload --port $env:BACKEND_PORT
```

Linux or macOS:

```bash
cp ../.env.example ../.env
# Edit ../.env and replace JWT_SECRET
export BACKEND_PORT="${BACKEND_PORT:-8000}"
.venv/bin/python -m dotenv -f ../.env run -- ./.venv/bin/uvicorn app.main:create_app --factory --reload --port "$BACKEND_PORT"
```

Git Bash on Windows:

```bash
cp ../.env.example ../.env
# Edit ../.env and replace JWT_SECRET
export BACKEND_PORT="${BACKEND_PORT:-8000}"
.venv/Scripts/python -m dotenv -f ../.env run -- ./.venv/Scripts/uvicorn app.main:create_app --factory --reload --port "$BACKEND_PORT"
```

`GET /health/live` returns `{"status":"live"}` once the process is up.

## Tests

Start only PostgreSQL from the repository root; test runs do not need a root `.env`. Keep 5432 as
the ordinary default, but export a different run-owned `POSTGRES_PORT` when required. Set
`TEST_DATABASE_URL` explicitly so every database-backed command targets that owned service.

PowerShell:

```powershell
if (-not $env:POSTGRES_PORT) { $env:POSTGRES_PORT = "5432" }
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:$env:POSTGRES_PORT/bmp_test"
docker compose up -d --wait db
```

Linux, macOS, or Git Bash:

```bash
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export TEST_DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:${POSTGRES_PORT}/bmp_test"
docker compose up -d --wait db
```

The harness reads `TEST_DATABASE_URL` only. Its local Compose default is
`postgresql+psycopg://postgres:postgres@127.0.0.1:5432/bmp_test`; that final name is a connection
template and is never created or dropped. Each database-backed pytest run creates an exact
`bmp_test_<32 lowercase hex>` database, holds an ownership lock, verifies its catalog OID, creates
only `p106_harness.probe`, and drops only that run-owned database after refusing unknown clients.

From `backend/`, run:

```bash
.venv/Scripts/pytest -m unit                          # database-free Windows loop
.venv/Scripts/pytest -m "not concurrency and not dst" # fast loop; includes PostgreSQL tests
.venv/Scripts/pytest                                  # full gate
.venv/Scripts/pytest --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml
```

Use `.venv/bin/pytest` on Linux/macOS. Override `TEST_DATABASE_URL` only with an explicit
`postgresql+psycopg` URL containing one host, username, password, and port; query, fragment,
multi-host, and socket forms are rejected before SQL. Missing PostgreSQL fails integration runs
rather than skipping them. The generated `coverage.xml` is untracked output and no numeric coverage
threshold applies at P1-06.

See `docs/deployment/local-development.md` for logs, database-shell access, persistence verification,
and destructive-reset safety. Python formatting, linting, type checking, and Git hooks are available
through [the main README](../README.md#quality-checks). Migration configuration begins in P2-01; its
explicit release-step mechanism remains deferred to DEP-01.
