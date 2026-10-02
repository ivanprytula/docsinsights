# docsinsights

**Updated:** 2026-09-29

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
| Frontend (Vite dev) | <http://localhost:5173> |
| Backend API | <http://localhost:8000> |
| API docs | <http://localhost:8000/docs> |
| Traefik dashboard | <http://localhost:8090/dashboard/> |
| Adminer | <http://localhost:8080> |
| Mailpit | <http://localhost:8025> |

## Running Locally

```sh
docker compose up -d
bun install
bun run --filter frontend dev
```

Backend runs in Docker automatically. See [development.md](./development.md) for local-only mode.

## Documentation

| Doc | Covers |
| --- | --- |
| [backend/README.md](./backend/README.md) | Backend setup, structure, conventions |
| [frontend/README.md](./frontend/README.md) | Frontend setup, structure, conventions |
| [development.md](./development.md) | Local dev workflow, `.env` config, Docker Compose services |
| [deployment-docker-compose.md](./deployment-docker-compose.md) | Self-hosted deployment |
| [docs/roadmap.md](./docs/roadmap.md) | Phase breakdown and planned work |
| [docs/c4-architecture.md](./docs/c4-architecture.md) | C4 context, containers and backend components; RAG walkthrough; dependency rules |
| [docs/skills-map.md](./docs/skills-map.md) | Capability coverage by domain |
| [docs/adr/](./docs/adr/) | Architecture Decision Records |

## Status

Early stage — auth module complete; extending authz (roles/permissions) next. RAG/document-ingestion domain work (`ingestion/`, `retrieval/`, `agentic_review/`, `authoring/`) planned as internal backend packages after auth solid, before any service split.

## License

MIT — see [LICENSE](./LICENSE).
