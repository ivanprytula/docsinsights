# Development

## Local Dev Stack

```bash
docker compose up -d db mailpit
uv sync
just prestart
cd backend && uv run fastapi dev  # terminal 1
bun run --filter frontend dev     # terminal 2
```

| Service | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Mailpit | http://localhost:8025 |

## Full Stack (Docker Compose)

```bash
docker compose run --rm backend uv run alembic upgrade head
docker compose watch
```

| Service | URL |
| --- | --- |
| Frontend + API | http://localhost:8000 |
| Adminer | http://localhost:8080 |
| Traefik | http://localhost:8090 |
| Mailpit | http://localhost:8025 |

**Note:** Traefik and full-stack services start slowly; check `docker compose logs` if needed.

## Code Structure

| Layer | Location |
| --- | --- |
| API endpoints | `backend/app/api/` |
| SQLModel models | `backend/app/models.py` |
| CRUD utilities | `backend/app/crud.py` |
| Frontend routes | `frontend/src/routes/` |
| Frontend components | `frontend/src/components/` |
| Email templates | `packages/react-email/` (generates to `backend/app/email-templates/`) |

## Configuration

| File | Purpose |
| --- | --- |
| `.env` | Local dev defaults; loaded by Docker Compose |
| `compose.yml` | Shared stack config |
| `compose.override.yml` | Local dev overrides (volumes, ports) |
| `compose.deploy.yml` | Production overrides (HTTPS, certs) |
| `.pre-commit-config.yaml` | Local linting/formatting rules |

**Restart after env changes:** `docker compose watch`

**Do not store secrets in `.env`.** Use `.env.example` as a template; secrets go to deployment platforms. See [deployment-docker-compose.md](./deployment-docker-compose.md).

## Code Quality

Run locally before pushing:

```bash
just check    # lint only (no fixes)
just fix      # format + lint fixes + generate SDK
```

CI runs the full suite in `ci.yml`.

## Pre-commit Hooks (Optional)

`prek` runs on every local commit if installed:

```bash
uv run prek install -f
```

To run manually:

```bash
uv run prek run --all-files
```

Changes made by `prek` must be re-staged before committing.
