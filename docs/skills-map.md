# Skills Map

The honest scoreboard. Every ladder point, where it lives in the codebase, and what
state it is actually in — not what I intend it to be.

**This is the skills-practice ledger, not the product spec.** DocsInsights is two
things at once: a real product idea (intelligent document navigation, semantic search, agentic review — see
[README](../README.md)) and a vehicle for demonstrating job-market skills the
product's actual problem size doesn't demand on its own. This file
tracks the second axis. The roadmap tracks the first —
each shipped phase is tagged **Product** or **Skills-practice** so it's
never ambiguous which reason a given piece of infrastructure exists for. A row
here with no product need is not a smell; it's the point — see "Deliberate
omissions" below for the mirror case (skills deliberately *not* practiced).

**Status vocabulary:**

| Status | Meaning |
| --- | --- |
| ✅ **Covered** | Implemented, tested, and load-bearing. A reviewer can read real code. |
| 🟡 **Partial** | Exists but shallow, or covered in one place where it should be several. |
| ⏳ **Planned** | Scheduled in a named phase. Not started. |
| ⏸️ **Deferred** | Deliberately postponed. Reason recorded. |
| ❌ **Skipped** | Decided against. Reason recorded — this is a *decision*, not a gap. |

**Depth tracking:**

Each ✅ row also has a *Depth* column tracking maturity of the implementation:

| Depth | Meaning |
| --- | --- |
| **L1: Breadth** | Feature exists, minimal viable implementation. Proof-of-concept level. |
| **L2: Robustness** | Feature exists with error handling, edge cases covered, tested. Production-ready. |
| **L3: Optimization** | Feature tuned for performance, measured trade-offs, documented. Interview-grade. |
| **L4: Generalization** | Feature abstracted to serve multiple use cases, extensible. Architectural pattern. |

Nothing here is a checkbox for its own sake. Where a skill has no honest job in this
product, it is marked ❌ with the reasoning, because a defended "no" is better signal
than a contrived "yes".

---

## Horizontal bar — breadth

### API design (REST / gRPC / GraphQL)

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| REST, domain-language endpoints | ✅ P1 | L1 | `app.ingestion.router` - `POST /documents/upload`, `GET /documents/`, `GET /documents/{id}`, `DELETE /documents/{id}`; `app.retrieval.router` - `POST /search` (optional `document_id`). Owner-scoped: a missing or foreign document returns 404 so ids cannot be probed (superusers can read and delete any document; search is always the caller's own). |
| OpenAPI → generated TS client | ⏳ P1 | — | `just generate-client` ready; CI will regenerate and run `tsc -b` — API drift fails the build. Schema-first contract. |
| GraphQL BFF | ❌ | — | Deferred. REST sufficient for phase 1; GraphQL added only if N+1 query patterns emerge. |

### Frontend to TypeScript + React level

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| React 19 + TS strict | ✅ P1 | L2 | `frontend/src/` — React 19+, TypeScript strict, Vite SWC. Type-strict, no `any`. ESLint + React hooks linting enforced. |
| Server state vs client state | ✅ P1 | L2 | Generated OpenAPI client (Axios, typed) for server; React state for UI (theme, language, document panel state). No external state lib — component-local is correct. |
| Streaming UI | ⏳ P2 | — | Planned: stream semantic search results + agentic review feedback as tokens arrive (SSE). |
| Accessibility | ⏳ P1 | — | Planned: keyboard navigation, ARIA labels, focus management. Playwright tests to verify keyboard-only operation. |

### SQL + data modeling

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| Relational modeling | ✅ P1 | L1 | `backend/app/ingestion/models.py` - `Document` (owner FK, cascade-delete) and `DocumentChunk` (one row per page, FK cascade-delete, `embedding vector(384)`). |
| Migrations | ✅ P1 | L1 | Alembic: initial schema (UUIDv7) plus `eb6f038d729c` (pgvector extension + `documentchunk.embedding`); upgrade/downgrade round-trip verified, `alembic check` clean. Per-domain model discovery wired in `alembic/env.py` (ADR-0003). |
| Vector store | ✅ P2 | L1 | pgvector on `documentchunk.embedding`, `NOT NULL`, dimensions read from the fastembed model registry (ADR-0005). Written on upload and queried by `POST /search`. No separate vector DB. |
| Query performance | ⏳ P3 | — | Planned: `EXPLAIN ANALYZE` on semantic search queries (vector search). |

### CI/CD, containers, secrets, DNS/HTTPS

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| Containers | ✅ P1 | L1 | Multi-stage `backend/Dockerfile` (Python 3.14 slim, builder stage, non-root `USER app`). `frontend/Dockerfile` for frontend build. |
| Compose (daily driver) | ✅ P1 | L1 | `compose.yml` unified: backend, frontend, postgres, mailpit. Health checks on all. `just dev` (hot-reload locally) and containerized variant ready. |
| CI pipeline | 🟡 P1 | L1 | `.github/workflows/ci.yml`: `uv sync` → `just check` (ruff, mypy, ty) → pytest. Frontend Playwright tests not yet in CI (run locally). |
| Secrets management | ✅ P1 | L1 | `.env.example` tracked (safe schema); `.env` gitignored. No secrets in code, args, or env vars. |
| DNS / HTTPS / TLS | ⏳ P4 | — | Deferred to deployment phase. |
| Kubernetes | ⏳ P4 | — | Deferred. kind proof-of-concept after MVP. |

### Security: authN/authZ, OWASP, secrets

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| AuthN | ⏳ P1 | — | JWT access + refresh rotation, argon2id hashing. Planned; not yet implemented. |
| AuthZ | ⏳ P1 | — | Resource checks: a user can only access their own documents. Planned. |
| OWASP Top 10 | ⏳ P2 | — | Input validation at boundaries (Pydantic schemas). Prompt injection defense (escaping, instruction hierarchy, output validation). Rate limiting deferred. |
| Input validation at trust boundaries | ✅ P1 | L1 | Pydantic schemas on all API endpoints (models.py). Chunk size, document name validated. |
| Prompt injection defense | ⏳ P2 | — | Planned: document content flows to LLM with escaping, structured output validation. ADR pending. |

### Observability: logs, metrics, traces

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| Structured logging | ⏳ P2 | — | Planned: JSON formatter (Uvicorn + stdlib), OTel trace/span injection. Redacted-fields set for sensitive data. |
| Metrics | ⏳ P3 | — | Prometheus client imported; not yet wired. Plan: RED on HTTP (request rate / errors / duration), search latency. |
| Traces | ⏳ P3 | — | OTel imported; propagation headers prepared. Full E2E trace deferred. |

---

## Vertical bar — backend depth (the differentiator)

### Async Python and concurrency models

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| async/await end-to-end | ⏸️ | — | Deferred (ADR-0003). Sessions are sync (`sqlmodel.Session` + `psycopg`) throughout; Phase 2 ingestion is CPU-bound (parsing/embedding), not I/O-bound, so async DB sessions buy nothing yet. Revisit only if async I/O becomes the real bottleneck — migrate all packages in one pass, not domain-by-domain. |
| Structured concurrency | ⏳ P2 | — | Planned: bounded document ingestion using `asyncio.TaskGroup`. |
| Backpressure + bounded concurrency | ⏳ P2 | — | Not implemented. Document embedding will use `asyncio.Semaphore` to bound concurrent calls. |
| Cancellation + timeouts | ⏳ P2 | — | Planned: `asyncio.timeout()` on LLM calls and embedding pipelines. |

### Distributed systems: queues, caching, consistency

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| Event log | ⏳ P3 | — | Kafka reserved for post-MVP (document ingestion events, agentic review decisions). |
| Caching | ⏳ P2 | — | Redis configured but unused. Plan: embedding cache (key=hash(chunk_content)), semantic search result cache. |
| Cache invalidation | ⏳ P2 | — | Not yet implemented. Plan: TTL-based invalidation for cached embeddings. |
| Consistency trade-offs | ⏳ P2 | — | Document searches use eventually-consistent cache. Document updates immediate on write. |

### System design at scale

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| Written design docs | ⏳ P2 | — | Planned: `docs/architecture.md` (C4 context → container → component). |
| Scaling narrative | ⏳ P4 | — | Planned: `docs/scaling.md` — system at 100 users → 100k → 10M; bottleneck analysis. |
| Capacity estimation | ⏳ P4 | — | Back-of-envelope: documents/user, storage growth, embedding cost per document. |
| Load testing | ⏳ P4 | — | k6 against semantic search + agentic review under concurrent load. |

### Performance profiling and tuning

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| Query profiling | ⏳ P3 | — | `EXPLAIN ANALYZE` on semantic search queries. Index strategy documented after measuring. |
| Frontend profiling | ⏳ P3 | — | React Profiler + Lighthouse; semantic search result rendering must not block UI. |
| Method, not anecdote | ⏳ P3 | — | `docs/performance.md` — measure → hypothesize → change → re-measure. |

---

## Emerging — front-loaded deliberately

### AI orchestration / RAG

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| LLM as reviewer, not chatbot | ⏳ P2 | — | Structured output (Pydantic model) for agentic review. Claude grades document clarity + consistency against a rubric. |
| RAG over document corpus | 🟡 P3 | L1 | Retrieval half works: chunk, embed, store, `POST /search` returns ranked passages with page numbers (see `docs/c4-architecture.md` walkthrough). Measured by the evaluation harness (`backend/evals/`). `POST /answer` adds a single-shot LLM answer with `[n]` page citations (tested with a fake model, live-checked on 2 questions). A keyword leg was tried and removed: no gain on the eval set (ADR-0006). Missing: reranker. |
| Embedding pipeline | 🟡 P2 | L1 | Upload -> parse PDF (pypdf, overlapping 250-word windows per page) -> embed (`ingestion/embedder.py`, fastembed bge-small, CPU) -> store, synchronously in the request (ADR-0005). No batching bounds, cache, or background worker yet. |
| Retrieval evaluation | ✅ P3 | L1 | `backend/evals/`: 75 labeled questions over GDPR and the AI Act, Recall@1/3/5 and MRR through the real ingest and search code on a throwaway pgvector container. Vector-only baseline Recall@1 0.33, Recall@5 0.65, MRR 0.45 on 75 questions (README explains the mixed label policy). Bootstrap intervals and saved JSON runs. Small set, run by hand: not CI-gated. A keyword-leg experiment was measured here and dropped (ADR-0006). |
| Cost + latency control | ⏳ P2 | — | LLM calls only on agentic review phase (once per document). Caching: identical chunks reuse cached embedding + review. |

### Agentic workflows and tool use (MCP)

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| MCP server | ⏳ P3 | — | Content-service mounts fastapi-mcp exposing document search + chunk retrieval (read-only). |
| Tool-use loop | ⏳ P2 | — | Planned: document ingestion pipeline (Dagster-style) with schema validation. |
| Agent orchestration (LangGraph) | ⏳ P3 | — | Planned: agentic review graph (retrieve → draft review → critique loop). SQLite checkpointing per document. |
| Human-in-the-loop | ⏳ P2 | — | Review results land in queue; human approves before publishing. |

### Vector databases and embedding pipelines

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| pgvector | 🟡 P2 | L1 | Cosine-distance queries (`<=>`) via `app.retrieval.search`, owner-scoped in SQL; `pgvector/pgvector:pg18` image in compose and CI. Sequential scan only: no HNSW/IVFFlat index yet. |
| **Why not Pinecone/Weaviate/Qdrant** | ❌ | — | At this corpus size (100s–1000s of documents), a dedicated vector DB is overkill. Document corpus size threshold recorded; will switch if needed. |

### Prompt / context engineering as engineering

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| Versioned prompts | ⏳ P2 | — | In-repo `backend/app/infrastructure/review_prompt.py`: system + user prompts. Changes flow through code review. |
| Snapshot tests | ⏳ P2 | — | Snapshot tests on review output parse results. Prompt changes produce reviewable diffs. |
| Structured output | ⏳ P2 | — | Pydantic model for review findings. LLM returns JSON or review fails gracefully. |
| Injection hardening | ⏳ P2 | — | Document content flows into LLM as JSON-escaped. Instruction hierarchy: review task → rubric → delimited content. |

### Fluency with AI coding assistants

| Facet | Status | Depth | Where |
| --- | --- | --- | --- |
| Repo is agent-legible | ✅ P1 | L1 | `CLAUDE.md`: workspace structure, layering rules, FastAPI conventions, code style. Pre-commit hooks enforce compliance. |
| Agent-enforceable invariants | ⏳ | — | Planned: `import-linter` contracts (domain never imports infrastructure). |
| Modulith package seam | ✅ P1 | L1 | ADR-0003: each domain (`ingestion/`, planned `retrieval/`, `agentic_review/`) owns its own `models.py`/`crud.py`/`router.py`. No shared `models.py` dumping ground; Alembic discovery made explicit per domain. Convention-enforced (no `import-linter` yet — deferred until package count justifies it). |
| Workflow documented | 🟡 P1 | L1 | CLAUDE.md documents the review bar (terse, small increments). Full `docs/ai-assisted-development.md` deferred. |

---

## Deliberate omissions

| Thing | Why not |
| --- | --- |
| Separate vector DB | Corpus too small to justify a second datastore initially. Threshold documented. |
| Production Kubernetes | Cloud Run fits the cost profile; kind proof-of-concept later. |
| Microservices on day one | Single monolith (backend + frontend). Split when a real architectural seam appears. |

---

## Deepening roadmap

Systematic approach to deepen coverage incrementally across all four dimensions
(horizontal breadth, vertical depth, emerging skills, and deliberate omissions).

### L1→L2 priorities (robustness: error handling, edge cases, testing)

| Focus | Current | Next step | Why |
| --- | --- | --- | --- |
| Streaming search results | L0 | Implement SSE for semantic search + agentic review feedback | Real-time UX expectation for document analysis |
| Structured concurrency | L0 | Bounded document ingestion using `asyncio.TaskGroup` | Prevent resource exhaustion under heavy upload |
| Input validation | L1 | Comprehensive Pydantic audit (all endpoints + error messages) | Trust boundary; every gap is a risk |
| Observability logging | L1 | Verify all error paths are logged (no silent failures) | Debugging production requires complete traces |
| Async profiling | L0 | Audit event-loop blocking with `slow_callback_duration` | Hidden sync calls become visible under load |

### L2→L3 priorities (optimization: measurement, tuning, documented trade-offs)

| Focus | Current | Next step | Why |
| --- | --- | --- | --- |
| Semantic search performance | L0 | Measure vector search latency (`EXPLAIN ANALYZE`); the keyword leg was already judged on quality and dropped (ADR-0006) | Claims about relevance are hollow without data |
| Embedding latency | L0 | Measure throughput under concurrent document ingestion | Capacity planning depends on real numbers |
| Prompt engineering | L0 | Snapshot tests for prompt changes; measure parse failure rate | Prompt regressions hide in iteration |
| LLM review cost | L0 | Track cost per document + parse failure rate; baseline metrics | Economics matter; establish baseline now |

### L3→L4 priorities (generalization: abstractions, patterns, extensibility)

| Focus | Current | Next step | Why |
| --- | --- | --- | --- |
| API design framework | L0 | Formalize REST endpoint naming; document when to add GraphQL | Valuable because *why* each is chosen |
| Caching strategy | L0 | Implement embedding + search result cache; document TTL trade-offs | Pattern emerges: cache taxonomy |
| Error handling | L0 | Formalize Result types; typed exceptions with structured feedback | Domain errors vs infrastructure errors |
| Concurrency patterns | L0 | Extract reusable bounded-concurrency wrapper; apply to embedding + ingestion | Pattern reuse across codebase |

### Emerging skills deepening

| Focus | Current | Next step | Why |
| --- | --- | --- | --- |
| RAG pipeline | L0 | Grow the golden set past 75 questions; retry a keyword leg only with rarity-aware ranking (ADR-0006) | Differentiator: measurement proves quality |
| Agentic workflows | L0 | LangGraph agent for document review; eval harness for regression detection | Agents without measurement are demos |
| Prompt versioning | L0 | Add CI checks for prompt drift; snapshot tests on fixed input set | Prompts are code; treat as such |
| Cost estimation | L0 | Back-of-envelope: tokens/document, documents/session, LLM cost/MAU | Matters for product pricing + pitch |

---

## Job description mapper

Given a JD requirement or technical skill, jump to the relevant code and depth level.

### Backend / API

| JD phrase | Where in DocsInsights | Depth | Gap? |
| --- | --- | --- | --- |
| "FastAPI / async Python" | `backend/app/main.py`, `backend/app/api/` | L1 | Event-loop profiling; full async stack audit |
| "SQL / relational modeling" | `backend/app/models.py`, `backend/app/alembic/` | L1 | Query performance audit with `EXPLAIN ANALYZE` |
| "REST API design" | `backend/app/api/routes/` (planned), `backend/app/models.py` (Pydantic) | L1 | Status code audit; breaking-change detection in CI |
| "Structured logging / observability" | `backend/app/core/` (planned) | L0 | Implement JSON logging + OTel injection |
| "Input validation" | `backend/app/models.py` (Pydantic schemas) | L1 | Audit all error messages for info leaks |
| "Domain-driven design" | `backend/app/ingestion/` (modulith seam, ADR-0003) | L1 | Full ports/adapters (repository protocols) deferred — deliberate, see ADR-0003 "when I would change this"; introduced only per-port when a second implementation needs swapping |

### Frontend / React

| JD phrase | Where in DocsInsights | Depth | Gap? |
| --- | --- | --- | --- |
| "React 19 / TypeScript strict" | `frontend/src/`, `package.json` | L2 | React Profiler traces; 60fps verification |
| "Client state management" | `frontend/src/` (local state, no external lib) | L1 | Document state ownership matrix |
| "SSE / streaming responses" | `frontend/src/` (planned) | L0 | Implement SSE parser for search + review streaming |
| "Accessibility (WCAG A11y)" | `frontend/src/` (planned) | L0 | Keyboard navigation + ARIA labels + Playwright tests |
| "API client generation" | OpenAPI → TypeScript (openapi-ts, CI regenerates) | L1 | Breaking-change detection in CI |

### Distributed systems / DevOps

| JD phrase | Where in DocsInsights | Depth | Gap? |
| --- | --- | --- | --- |
| "Docker / containerization" | `backend/Dockerfile`, `frontend/Dockerfile` | L1 | Add image scanning; base digest pinning |
| "Docker Compose" | `compose.yml` (backend, frontend, postgres, mailpit) | L1 | Add observability stack profile |
| "CI/CD pipeline" | `.github/workflows/ci.yml` | L1 | Add frontend tests + dependency scanning gates |
| "Monitoring / observability" | Planned | L0 | Wire Prometheus metrics + Grafana dashboard |
| "Secrets management" | `.env.example` (safe schema), `.env` (gitignored) | L1 | Audit for hardcoded secrets |

### AI / LLM / RAG

| JD phrase | Where in DocsInsights | Depth | Gap? |
| --- | --- | --- | --- |
| "LLM-based document review / structured output" | Planned | L0 | Implement review Pydantic model + streaming feedback |
| "Prompt engineering / versioning" | Planned | L0 | In-repo prompts, snapshot tests, CI drift detection |
| "Prompt injection defense" | Planned | L0 | Escaping, instruction hierarchy, output validation |
| "RAG / semantic search" | `backend/app/retrieval/`, `backend/evals/` | L1 | Recall@k eval is not CI-gated; golden set is small |
| "Cost + latency control" | Planned | L0 | Cache embeddings + reviews; measure metrics |
| "Agentic workflows / tool use" | Planned | L0 | LangGraph review loop with human-in-the-loop |

---

## How to read this as a reviewer

Fastest path to judging whether I can actually do this work:

1. `backend/app/models.py` — the data schema with no framework
2. `backend/app/api/` — the REST endpoints (planned domain language)
3. `CLAUDE.md` — the architecture and code standards
4. This file — both breadth (what exists) and depth (how mature)
