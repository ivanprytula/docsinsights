# docsinsights

Document ingestion, retrieval, and agentic review platform. Backend-first modular monolith; RAG-oriented domain work builds on top of the auth/authz foundation.

Built on [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template); see [LICENSE](./LICENSE) for attribution.

## Stack

| Layer | Tech |
| --- | --- |
| Backend | FastAPI, SQLModel, PostgreSQL, Alembic |
| Frontend | React, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Auth | JWT (login + email recovery) — role/permission authz in progress |
| Infra | Docker Compose, Traefik |
| Email (dev) | Mailpit |
| Testing | pytest (backend), Playwright (e2e) |
| Package manager (frontend) | Bun (workspaces: `frontend`, `packages/*`) |

## Local Services

| Service | URL |
| --- | --- |
| Frontend (Vite dev) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Traefik dashboard | http://localhost:8090/dashboard/ |
| Adminer | http://localhost:8080 |
| Mailpit | http://localhost:8025 |

## Running Locally

```sh
docker compose up -d db adminer backend mailpit proxy
bun install
bun run --filter frontend dev
```

## Docs

| Doc | Covers |
| --- | --- |
| [backend/README.md](./backend/README.md) | Backend setup, structure, conventions |
| [frontend/README.md](./frontend/README.md) | Frontend setup, structure, conventions |
| [development.md](./development.md) | Local dev workflow, `.env` config, Docker Compose services |
| [deployment-docker-compose.md](./deployment-docker-compose.md) | Self-hosted deployment |

## Status

Early stage — auth module under review before extending authz (roles/permissions) as the first real feature. RAG/document-ingestion domain work (`ingestion/`, `retrieval/`, `agentic_review/`, `authoring/`) comes after auth is solid, built inside this backend as internal packages before any service split.

## License

MIT — see [LICENSE](./LICENSE).
