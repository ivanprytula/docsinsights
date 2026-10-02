# Product Roadmap

Short PRDs for what's actually shipped, one per phase, product-first — not the
skill-coverage ladder (`skills-map.md`) or the reasoning behind each choice
(`docs/adr/`). This is the doc to read to answer "what does the product do
today and why does that feature exist," in order.

Each entry: the problem, the decision, what shipped. Player-facing behavior
is authoritative in specs (e.g., [README](../README.md)) — this doc points there
instead of restating it.

## Product vs. skills-practice

Two things are true about this repo at once, and conflating them is exactly
what produced overlapping plan files with no roadmap: **DocsInsights is a real
product idea** (intelligent document navigation, semantic search, agentic review)
**and a vehicle for practicing job-market skills** (RAG pipelines, async job queues,
Kubernetes orchestration) that the product's actual problem size doesn't demand
on its own — see [ADR-0001](./adr/0001-record-architecture-decisions.md).

Every phase below is tagged:

- **Product** — the app genuinely needed this to be a better document-navigation
  tool. Would exist even at a much smaller portfolio scope.
- **Skills-practice** — the app works without it; it's here because the job hunt
  needs the skill demonstrated somewhere, and this product is the vehicle.
  `skills-map.md` is the ledger for *this* axis — every skills-practice phase
  has a row there.

A phase can be both. Tag reflects the primary reason it exists, not every
side effect.

---

## Phase 1 — Auth & user identity

**Tag:** Product. User-bound document management requires auth as a foundation.

**Problem:** the initial scaffold has no user identity or session management.
Uploading and organizing documents requires knowing who owns what.

**Decision:** implement email/password authentication with stateless JWT tokens (access
+ refresh), session persistence, and role field (schema-only) as foundation for Phase 2
authorization. Lean on industry-standard patterns (Argon2+bcrypt hashing via `pwdlib`,
refresh-token rotation) rather than custom security.

**Shipped:**

- `User` model with `role` enum field (default `"user"`)
- `POST /users/signup` (register), `POST /login/access-token` (login), `POST /login/refresh-token` (refresh)
- JWT middleware (`get_current_user`, `get_current_active_superuser`)
- Password hashing via `pwdlib` (Argon2 primary, bcrypt fallback with auto-upgrade)
- Stateless refresh tokens (rotated on use, no server-side revocation)
- Password recovery/reset flow (`POST /password-recovery/{email}`, `POST /reset-password/`)
- Frontend login/signup/recover/reset forms with validation
- Comprehensive test coverage for auth flows

**Rules:** [README § Authentication](../README.md#authentication) (if documented)

**ADRs:** [ADR-0004: Refresh Tokens and Roles](./adr/0004-auth-refresh-tokens-and-roles.md)

---

## Phase 2 - Document ingestion & vectorization

**Tag:** Product (the vectorization half doubles as Skills-practice: RAG, pgvector).

**Problem:** documents can't be searched by meaning until their text is extracted
and turned into vectors. Search and review (Phases 3-4) need that stored first.

**Decision:** PDF only, pages split into overlapping 250-word windows (page number kept for citations; bge-small truncates at 512 tokens),
embedded on CPU with fastembed `bge-small-en-v1.5`, stored in pgvector alongside
the chunk. Embedding happens synchronously in the upload request. The embedder
lives in `ingestion/` so retrieval can depend on ingestion, not the reverse.

**Shipped:**

- `POST /documents/upload` (PDF): parse, chunk, embed, and store a document with its chunks in one transaction
- `GET /documents/`, `GET /documents/{id}`, `DELETE /documents/{id}`, owner-scoped (superuser bypass)
- `DocumentChunk.embedding` as `vector(384)`, `NOT NULL`; pgvector extension via migration
- Clear 422s for encrypted, unreadable, and text-less PDFs
- Verified end to end: upload via the API stores the document, chunks, and vectors

**Not shipped:** search over the vectors, ANN index, DOCX, OCR, background embedding.

**ADRs:** [ADR-0002: RAG stack](./adr/0002-rag-stack-and-retrieval-design.md), [ADR-0003: Modulith seam](./adr/0003-modulith-package-seam.md), [ADR-0005: Embedder ownership and pgvector](./adr/0005-embedder-ownership-and-pgvector-storage.md)

---

## Not yet started

- **Phase 3 (semantic search)** — vector similarity, ranking, filtering.
- **Phase 4 (agentic review)** — multi-turn LLM interaction, structured output.
- **Phase 5+ (cloud deploy, scaling)** — see README; decisions pending.

---

## How this doc stays honest

A phase only gets an entry here once it's shipped and verified, mirroring
`skills-map.md`'s rule: this describes what exists, not what's intended.
When a new phase lands, add one entry above "Not yet started," cite the
ADR(s) that defend it, and link relevant spec sections if behavior changed.
If a decision later gets superseded, the phase entry stays as shipped-then, not
rewritten — the ADR's own Resolution/Status field is where the correction lives.
