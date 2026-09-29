# ADR-0003: Modulith Package Seam for Domain Packages

**Status:** Accepted
**Date:** 2026-09-28
**Deciders:** Ivan

## Context

The current backend is a flat template layout: one `models.py`, one `crud.py`, `api/routes/*.py` per resource. This is fine for `User`/`Item`, but CLAUDE.md commits to adding `ingestion/`, `retrieval/`, `agentic_review/`, `authoring/` as "internal backend packages" before any service split (a modulith). Nothing in the current structure defines what an "internal package" actually is — without a seam, `Document`/`Chunk` models would land in the same flat `models.py` next to `User`, and the modulith stays aspirational instead of real.

Alembic currently discovers all tables via a single `from app.models import SQLModel` import (see `alembic/env.py`) — this must keep working as new domains add their own tables. `crud.py` is a flat file with no per-domain grouping. All sessions are synchronous (`sqlmodel.Session`, not `AsyncSession`).

## Decision

Each domain gets a **self-contained package** under `backend/app/`, owning its own models, CRUD, and router:

```
backend/app/
  ingestion/
    __init__.py
    models.py       # Document, Chunk (SQLModel tables + Pydantic schemas)
    crud.py         # create_document, list_chunks, etc.
    router.py        # APIRouter for /documents/*
  retrieval/
    __init__.py
    models.py         # if retrieval needs its own persisted state (e.g. search logs) — empty otherwise
    embedder.py       # Embedder protocol + fastembed implementation
    hybrid_search.py
    reranker.py
    router.py
  agentic_review/
    ...
```

**Rules for the seam:**

1. **Models stay per-package.** `ingestion/models.py` defines `Document`/`Chunk` tables. The existing `app/models.py` keeps `User`/`Item` — it is not a dumping ground for new domains. There is no single shared `models.py` going forward.
2. **Alembic registers all domains explicitly.** `alembic/env.py`'s `target_metadata = SQLModel.metadata` still works *only if every domain's models module is imported somewhere before Alembic runs* — add explicit imports in `alembic/env.py` (`from app.ingestion.models import Document, Chunk  # noqa`) rather than relying on one central import. This is the one place flat-file convenience gave us an implicit guarantee that per-package layout must now make explicit.
3. **CRUD stays per-package.** `ingestion/crud.py` never imports from `retrieval/crud.py` directly — if retrieval needs ingestion data, it depends on `ingestion`'s public functions/models, not the other way, and the dependency direction only goes one way (retrieval depends on ingestion, not vice versa; agentic_review depends on retrieval + ingestion).
4. **Routers wire in centrally.** `api/main.py` gains one `include_router` per domain, same pattern as today's `items`/`users`. Prefix stays domain-language (`/documents`, `/search`), not `/api/ingestion`.
5. **No cross-package reach-through.** A package imports another package's `models.py`/`crud.py` only for its declared public surface (e.g., `retrieval` imports `ingestion.models.Chunk` to read it, never `ingestion.crud`'s internals to write it). No import-linter enforcement yet (per CLAUDE.md, deferred) — this is a discipline rule until the package count justifies the tooling.
6. **Sync sessions for now.** Phase 2 ingestion (PDF parsing, embedding) runs CPU-bound work; it does not need async DB I/O to get the async benefit — the CPU work is the bottleneck, not the DB round-trip. Stay on `sqlmodel.Session` consistent with the rest of the app. Async execution (Phase 5 webhooks/job queues) is a separate concern (background task/worker, not `AsyncSession`) and doesn't retroactively require this ADR's revisit.

## When I would change this

- **If package count grows past ~4-5 and cross-package imports start getting sloppy:** adopt `import-linter` (already precedented in term-rush) to enforce the one-way dependency rule machine-side instead of by convention.
- **If a domain's CRUD needs to compose across domains transactionally** (e.g., delete a Document must cascade to retrieval's index state): add an explicit facade function in the *owning* domain (`ingestion.crud.delete_document_cascade()`) rather than letting `retrieval` reach into `ingestion`'s session/transaction.
- **If async I/O becomes the actual bottleneck** (not just CPU-bound embedding): migrate to `AsyncSession` across all packages in one pass, not domain-by-domain — mixed sync/async sessions on one engine is a known footgun.

## Consequences

- `Document`/`Chunk` models never touch the existing flat `app/models.py` — zero risk of merge conflicts or accidental coupling with `User`/`Item`.
- Alembic migrations remain one command (`alembic revision --autogenerate`), but env.py's import list grows by one line per new domain — a visible, reviewable diff each time a domain is added.
- The modulith stays real (enforced by package boundaries + convention) rather than aspirational (a claim in CLAUDE.md with no structural backing).
