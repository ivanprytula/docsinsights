# FastAPI Project - Frontend

The frontend is built with [Vite](https://vitejs.dev/), [React](https://react.dev/), [TypeScript](https://www.typescriptlang.org/), [TanStack Query](https://tanstack.com/query), [TanStack Router](https://tanstack.com/router), [Tailwind CSS](https://tailwindcss.com/), and [shadcn/ui](https://ui.shadcn.com/).

## Requirements

- [Bun](https://bun.sh/)

## Quick Start

From the project root, install the dependencies and start the frontend development server:

```bash
bun install
bun run dev
```

Then open <http://localhost:5173/> in your browser.

Run `just prestart` and `cd backend && uv run fastapi dev` with PostgreSQL running in Docker Compose. See [../development.md](../development.md) for the complete setup.

To serve the frontend with FastAPI, run `bun run build` from the `frontend` directory and open `http://localhost:8000`.

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
