# Local development with Docker Compose

Docker Compose runs the FastAPI backend and PostgreSQL for local development. The frontend joins the
local stack in P6-01.

## Prerequisites

- Docker Desktop or Docker Engine using Linux containers with Docker Compose.
- An available local TCP port 8000 for the backend and 5432 for PostgreSQL. Override them with the
  non-secret shell variables `BACKEND_PORT` and `POSTGRES_PORT` when needed.

`backend/requirements.txt` is the generated Linux-container/deployment lock. It deliberately contains
Linux-only `uvloop` and omits Windows-only transitive packages. Do not install that file into a Windows
development environment. Native Windows development installs from the editable `pyproject.toml`
source instead:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

## First start

From the repository root, create the ignored local environment file:

PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux, macOS, or Git Bash:

```bash
cp .env.example .env
```

Edit `.env` and replace the deliberately invalid `JWT_SECRET` sentinel with at least 32 random UTF-8
bytes. Do not commit `.env`. The PostgreSQL username, password, and database have non-secret local
defaults in `compose.yaml`; exported `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` values
override them without changing the file.

Build and start both services, waiting for their health checks:

```bash
docker compose up --build --wait
docker compose ps
```

The database health check runs every 5 seconds with a 5-second timeout, a 10-second start period, and
10 retries. The backend health check uses Python's standard-library HTTP client every 5 seconds with a
3-second timeout, a 10-second start period, and 10 retries.

Confirm the backend response:

PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
```

Linux, macOS, or Git Bash:

```bash
curl --fail http://127.0.0.1:8000/health/live
```

The response is `{"status":"live"}`.

## Logs and database shell

Follow logs for either service:

```bash
docker compose logs --follow backend
docker compose logs --follow db
```

Open an interactive PostgreSQL shell using the values already present inside the container:

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

## Stop, restart, and persistence

Stop the containers while retaining the named PostgreSQL volume:

```bash
docker compose down
```

Start them again and wait for health:

```bash
docker compose up --wait
```

To prove data survives that cycle, open the database shell and run:

```sql
CREATE TABLE IF NOT EXISTS p1_04_persistence_probe (
    marker text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO p1_04_persistence_probe (marker)
VALUES ('survives-compose-down')
ON CONFLICT (marker) DO NOTHING;
```

Exit with `\q`, run `docker compose down`, then `docker compose up --wait`. Reopen the shell and run:

```sql
SELECT marker FROM p1_04_persistence_probe WHERE marker = 'survives-compose-down';
DROP TABLE p1_04_persistence_probe;
```

The `SELECT` must return `survives-compose-down` before the probe table is removed.

## Destructive local reset

> **Warning:** The following command permanently removes this Compose project's PostgreSQL volume and
> all local data in it. Confirm the project name and take a dump first if the data matters.

Optional pre-reset dump on PowerShell:

```powershell
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' |
    Set-Content -Encoding utf8 local-development-backup.sql
```

Optional pre-reset dump on Linux, macOS, or Git Bash:

```bash
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  > local-development-backup.sql
```

After explicit confirmation that the data may be destroyed:

```bash
docker compose down -v
docker compose up --build --wait
docker compose ps
```

`down -v` removes only volumes declared by this Compose project. Check its output and
`docker volume ls` before continuing if any unexpected volume is named. Full restore verification is
owned by later backup-and-recovery tasks; the dump here is a local safety measure.
