# Frontend — docsinsights

**Updated:** 2026-09-29

Tech stack: [Vite](https://vitejs.dev/), [React](https://react.dev/), [TypeScript](https://www.typescriptlang.org/), [TanStack Query](https://tanstack.com/query), [TanStack Router](https://tanstack.com/router), [Tailwind CSS](https://tailwindcss.com/), [shadcn/ui](https://ui.shadcn.com/).

## Requirements

- [Bun](https://bun.sh/)

## Quick Start

From project root:

```bash
just up
```

Then open <http://localhost:5173/> in your browser (Vite dev server auto-starts).

To stop: `just down`

## Development

Install dependencies and start dev server:

```bash
bun install
bun run --filter frontend dev
```

Frontend: <http://localhost:5173/>
Backend API: <http://localhost:8000/docs> (must be running)

To build for production (served by FastAPI):

```bash
bun run --filter frontend build
# Then: http://localhost:8000
```

Check `frontend/package.json` for available commands.

## Generate Client

**Automatically (recommended):**

```bash
just generate-client
```

**Manually:**

```bash
# Backend must be running
curl http://localhost:8000/api/v1/openapi.json > frontend/openapi.json
bun run --filter frontend generate-client
```

Regenerate whenever backend API changes.

## Remote API

Set `VITE_API_URL` in `frontend/.env` to use a different backend:

```env
VITE_API_URL=https://my-domain.example.com
```

## Structure

| Path | Purpose |
| --- | --- |
| `src/` | Main code |
| `src/client/` | Generated OpenAPI client |
| `src/components/` | React components (shadcn/ui in `ui/`) |
| `src/hooks/` | Custom hooks |
| `src/lib/` | Utilities |
| `src/routes/` | Pages and routing |
| `public/` | Static assets |

## E2E Tests (Playwright)

Start the stack:

```bash
docker compose run --rm backend uv run alembic upgrade head
docker compose up -d --wait backend
```

Run tests:

```bash
bunx playwright test        # headless
bunx playwright test --ui   # with UI
```

Cleanup:

```bash
docker compose down -v
```

Test files are in `tests/`. See [Playwright docs](https://playwright.dev/docs/intro) for reference.
