# docsinsights — working agreement

## The owner reads every line

This is a portfolio project whose purpose is that the owner genuinely knows his own codebase and can defend any line of it in an interview. Code he cannot account for is worse than no code.

**Therefore, for any agent working here:**

- Ship **one module or concept at a time**, then stop for review. Never dump many files in a single turn.
- Prefer boring, explicit code. Cleverness that needs decoding is a liability.
- Flag anything deserving extra scrutiny: subtle logic, edge cases, places you were uncertain or got something wrong.
- Do not commit unless asked. The owner tests and verifies himself.

## Be terse

Verbose prose costs the reader attention. Density is a feature.

- **Comments only where the code cannot speak.** A non-obvious decision, a magic constant's origin, a deliberate trade-off. Never restate what the line does.
- **Docstrings: Google style, one-line summary.** Every public function and method. Extend only for genuinely non-obvious contracts. No Args/Returns blocks that repeat the type signature.
- **No section-header comments** (`# --- helpers ---`), no banner art, no narration.
- **Commit messages:** subject line with conventional prefix (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`), plus body only when the *why* isn't evident. No bullet summaries of the diff — the diff is the summary.
- **PR bodies:** what changed, why, how to verify. Three short sections maximum.
- **Chat replies:** lead with the answer. Skip preamble, skip recap of what was just read, skip closing summaries that repeat the body.

ADRs are the deliberate exception — they carry reasoning, and reasoning is their point. Keep them structured and skimmable, not chatty.

## Design Principles

Follow ACROSS: **A**bstractions & Decomposition, **C**omposition by Default, escape the **R**abbit hole, **O**ptimize for change, **S**imple as possible, **S**creaming contract.

See `~/.claude/CLAUDE.md` for the full ruleset.

## Git Workflow

- **Branch strategy:** Feature branches from `main` as `feature/<name>`. Never commit directly to `main`.
- **Commit format:** [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).
- **Staging:** Stage changes for review. Do not commit or push unless asked.
- **No trailers:** No `Co-Authored-By:` or tool-attribution lines in commits or PR bodies.

## Code Style

- **Type hints:** Every public function and method, including return types. Use `|` for unions (`str | None`), not `Optional[str]`.
- **Docstrings:** Google style, one-line summary. Add parameters/returns only if non-obvious from the signature.
- **FastAPI Annotated style:** Use `Annotated[Type, Depends(...)]` for dependencies (creates reusable type aliases: `SessionDep = Annotated[Session, Depends(...)]`). Path parameters use `Annotated[str, Path(...)]` to validate at the boundary.
- **Linting & formatting:** `ruff` for Python (config in `pyproject.toml`), `biome` for TypeScript/JSX.
- **Type checking:** `ty` for Python (gates `just check`). `pyrefly` runs as a manual pre-commit hook / `just type-check-strict` for stricter, opt-in checking — not part of the automatic gate.
- **Filesystem:** Use `pathlib.Path` — never `os.path`.
- **String formatting:** Prefer f-strings over `str.format()` or `%`.
- **Error handling:** EAFP (Easier to Ask for Forgiveness than Permission) — handle the exception rather than pre-check.
- **Request validation:** Pydantic models for all request bodies.
- **Python idioms:** Comprehensions, generators, decorators, context managers.
- **No hardcoded references:** Avoid hardcoding file paths or line numbers in comments, docstrings, and docs. A path reference goes stale the moment code moves. Name the function/class instead (e.g., "see `authenticate` function", not "see `backend/app/crud.py:42`").

## SQLModel & Alembic Patterns

- **Models:** Define in `backend/app/models.py`. Use `SQLModel` with `sa_column=Column(...)` for database-specific constraints.
- **Migrations:** Create a migration after every model change (Alembic in `backend/app/alembic/versions/`).

```bash
cd backend && uv run alembic revision --autogenerate -m "Add column X to User"
uv run alembic upgrade head
```
- **CRUD:** Keep CRUD logic in `backend/app/crud.py`, organized by entity. Use SQLModel's `session.exec(select(...))` pattern.
- **Frozen Pydantic models:** Use for domain entities and value objects (`model_config = ConfigDict(frozen=True)`).

## API Contract



- **Endpoints speak domain language:** `POST /users/`, `GET /items/{id}`, not `/api/process`.
- **Status codes are meaningful:** `200` success, `201` created, `400` bad request, `401` unauthorized, `403` forbidden, `404` not found, `422` validation error (Pydantic), `500` server error.
- **Typed results over bools:** Return `User | None` or a domain enum, not bare `True`/`False`.
- **Error responses:** Generic messages to clients (`"Resource not found"`), full exceptions logged server-side only. No credentials, paths, or schema details in error messages.

## Testing

- **Structure:** Unit tests in `backend/tests/unit/`, integration tests in `backend/tests/integration/`.
- **E2E with Playwright:** Tests in `frontend/tests/`, run via `docker compose` (backend must be running).
- **Naming:** Test functions describe the scenario: `test_authenticate_with_valid_email_succeeds`, not `test_auth`.
- **Coverage:** Run locally: `just test`. CI enforces 90% coverage on backend.

## Frontend (Bun + React + TypeScript)

- **Workspace:** Root `package.json` defines Bun workspaces (`frontend`, `packages/*`). Use `bun run --filter frontend <script>` or `bun run <script>` at project root.
- **Client SDK:** Generated from backend OpenAPI schema. Regenerate when API changes: `just generate-client`.
- **Component structure:** `src/components/` for UI, `src/hooks/` for custom hooks, `src/routes/` for pages.
- **Styling:** Tailwind CSS + shadcn/ui components in `src/components/ui/`.
- **Testing:** Playwright E2E tests; run with `bunx playwright test` (requires running Docker stack).

## Architecture

**Current state:** Modular monolith. Backend is a single FastAPI service; frontend is React + TypeScript.

**Planned (after auth is solid):** RAG/document-ingestion domain as internal backend packages (`ingestion/`, `retrieval/`, `agentic_review/`, `authoring/`) — no separate services yet. Service split happens only when a real architectural seam appears (e.g., OCR/document-processing CPU scaling).

**No layering enforcement yet** (unlike term-rush's import-linter), but follow this mental model:
- `api/` — FastAPI routes, dependency injection, request/response mapping
- `crud.py` — Database operations
- `models.py` — SQLModel entities and Pydantic schemas
- `core/` — Config, auth, security
- `utils.py` — Helpers (password hashing, email, etc.)

## Environment & Configuration

- `.env` — Local development defaults (DB creds, API keys, etc.). Tracked in git for reference; secrets overridden at deploy time.
- `compose.yml` — Shared Docker Compose config (db, mailpit, backend, frontend ports).
- `compose.override.yml` — Local dev overrides (volume mounts, hot-reload).
- `compose.deploy.yml` — Production overrides (HTTPS, certs via Traefik).

**Do not store secrets in `.env`.** At deployment, use environment variables, secrets managers, or `.env.local` (gitignored).

## Verification Checklist

Before claiming work is done:

1. `just check` — code quality (ruff + ty) + tests pass
2. Run affected tests: `just test backend/tests/unit/...` (for backend), `just test-frontend` (for Playwright)
3. Check error messages — generic wording, no info leaks
4. Rebuild locally: `docker compose build && docker compose up -d && curl http://localhost:8000/api/v1/utils/health-check && docker compose down`
5. **Markdown files:** Spell-check, code block language tags, no hardcoded line numbers

## Justfile Commands

- `just format` — Ruff format + biome lint (fixes)
- `just lint` — Type-check + style checks (no fixes)
- `just prestart` — Run migrations + seed initial data
- `just test` — Backend unit tests with coverage report
- `just generate-client` — Generate OpenAPI client + lint
- `just test-compose` — Full Docker Compose test (build, start, test, cleanup)
- `just check` — All quality gates (lint + format + test)

## Workspace Structure

```text
backend/
  app/
    api/              # FastAPI routers, dependency injection
      routes/         # Grouped endpoints (users, items, login, etc.)
    core/             # Config, auth, security constants
    models.py         # SQLModel entities + Pydantic schemas
    crud.py           # Database operations
    utils.py          # Helpers (password, email, etc.)
    main.py           # FastAPI app initialization
    initial_data.py   # Seed data
  alembic/            # Database migrations
  tests/
    unit/             # Domain + CRUD tests
    integration/      # API + adapter tests
    conftest.py       # Fixtures
    utils/            # Test helpers
  pyproject.toml      # Backend dependencies
  Dockerfile          # Monolith image (multi-stage: builds frontend, then backend)

frontend/
  src/
    client/           # Generated OpenAPI client (not committed)
    components/       # React components (shadcn/ui in ui/)
    hooks/            # Custom hooks
    lib/              # Utilities
    routes/           # Pages (TanStack Router)
  tests/              # Playwright E2E tests
  vite.config.ts      # Vite config (SWC, Tailwind)
  openapi-ts.config.ts  # Client generation config
  package.json        # Frontend dependencies
  Dockerfile.playwright  # E2E test runner image (used by compose.override.yml)

packages/
  react-email/        # Email templates (React Email component library)
    emails/           # Template components
    ui/               # Shared email UI components
  (future: shared libs)

.github/workflows/
  ci.yml              # Unified CI: code quality, backend tests, e2e tests, smoke test

Root:
  justfile            # Task automation
  compose.yml         # Local dev stack
  .pre-commit-config.yaml  # Pre-commit hooks (prek: ruff, biome, actionlint, typos)
  pyproject.toml      # Backend workspace config
  package.json        # Frontend workspace config (Bun)
  CLAUDE.md           # This file
  README.md           # Project overview
  development.md      # Dev setup guide
  deployment-docker-compose.md  # Self-hosted deployment
```

## Next Steps (Planned, Not Yet Started)

1. **Auth review & extension:** Read auth module end-to-end, then design + build role/permission-based authz.
2. **ADR process:** Start `docs/adr/` directory for significant design decisions (auth design, ingestion strategy, etc.). Each ADR gets a **"When I would change this"** section — no reversal condition = advertisement, not a decision.
3. **Skills map:** Create `docs/skills-map.md` to track capability coverage honestly (Covered/Partial/Planned/Deferred/Skipped).
4. **RAG/ingestion domain:** After auth is solid, build as internal backend packages (no separate services yet).

## Key Invariants

- **Owner accountability:** Every line must be defensible. If uncertain, flag it.
- **One thing at a time:** Ship a module, stop for review, iterate.
- **Boring code wins:** Explicit beats clever.
- **Domain language:** Names scream intent. `authenticate`, `create_item`, not `process`, `handle`.
- **Tests pin behavior, not implementation:** Tests are the spec; regressions surface immediately.
- **Docs are contracts:** When functionality changes, update docs first. A stale doc is worse than no doc.
