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
& refresh), session persistence, and role field (schema-only) as foundation for Phase 2
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

## Phase 3 - Semantic search

**Tag:** Product. Uploaded documents are only useful if a question can find the right passage.

**Problem:** after Phase 2 the vectors sit in the database but nothing reads them. A user cannot
ask "do I need AWS?" and get the page that answers it.

**Decision:** vector-only search over the caller's own chunks. The query is embedded with the
same model as the chunks, and Postgres ranks chunks by cosine distance (pgvector). `POST`
rather than `GET` so query text stays out of URLs and access logs. A missing or foreign
`document_id` returns 404 (same for document read and delete) so ids cannot be probed. No
query prefix: it changed no rankings in a check on real chunks (ADR-0005).

**Shipped:**

- `POST /search` with `query`, `limit` (1-20, default 5) and optional `document_id`; returns filename, page, passage and score per hit
- Owner scoping inside the SQL query, so another user's passages never enter the result set
- Whitespace collapsed at chunking, so returned passages are readable (pypdf can emit one word per line)
- `GET` and `DELETE /documents/{id}` return 404 instead of 403 for documents the caller cannot see
- Ownership check and similarity query shared with `POST /answer` (an LLM answer over the top passages, not yet a roadmap phase), so both return the same 404 for foreign documents
- Checked on real data: "aws" and a paraphrase ("do I need to know Amazon Web Services?") both rank the passage containing the AWS requirement first

**Known limits (not shipped):**

- No keyword leg in use: acronym and exact-term queries rank weakly. A full-text leg was built, measured and removed because it did not beat vector-only ([ADR-0006](./adr/0006-keyword-leg-tried-not-adopted.md))
- No score threshold: scores are compressed (0.46-0.64 in the check), so only ordering is meaningful and weak matches still return
- No vector index (sequential scan) and no reranker
- Quality is measured on 75 questions only; see [Retrieval evaluation](#retrieval-evaluation) for the baseline
- No frontend screen for upload or search; the feature is API-only

**ADRs:** [ADR-0002: Search endpoint, `POST` now and `QUERY` later](./adr/0002-rag-stack-and-retrieval-design.md), [ADR-0003: Modulith seam](./adr/0003-modulith-package-seam.md), [ADR-0004: 404 for foreign documents](./adr/0004-auth-refresh-tokens-and-roles.md), [ADR-0005: Embedder ownership and pgvector](./adr/0005-embedder-ownership-and-pgvector-storage.md).

**Architecture:** [C4 architecture](./c4-architecture.md) has the component view and an end-to-end walkthrough.

---

## Retrieval evaluation

**Tag:** Product, and Skills-practice (measuring a RAG pipeline). Retrieval changes need a number, not a hand check.

**Problem:** Phase 3 quality was judged by eye on a few documents, so no change (keyword leg, threshold, index) could be shown to help or hurt.

**Decision:** a golden set of questions, each labeled with the document and PDF pages that answer it, run through the real ingestion and search code against a throwaway pgvector container. Metrics are Recall@1/3/5 and MRR, over two public EU regulations (GDPR, AI Act). The PDFs stay out of the repo (EUR-Lex reuse terms); the README says where to download them. Labels come from the PDF headings, not from search results, so the set does not bend toward the current ranking.

**Shipped:**

- `python -m evals.retrieval` from `backend/`: ingests the corpus, prints the metrics and the top hits for every question that missed rank 1
- `evals/metrics.py` (`recall_at_k`, `mean_reciprocal_rank`) and `evals/questions.json` (75 questions: 28 original, 47 added with operative-article labels only)
- Tests in `tests/evals/` using a fake embedder, so they need no model download
- Baseline, vector-only (786 chunks, 75 questions): Recall@1 0.33, Recall@3 0.52, Recall@5 0.65, MRR 0.45. The 28 original questions score 0.50 / 0.64 / 0.71 / 0.58; the 47 added ones score lower partly because their labels exclude recitals (see README)
- Bootstrap intervals in the report and each run saved as JSON under `evals/results/`
- A keyword leg was measured against the same set (Recall@1 0.32, Recall@5 0.64, MRR 0.46) and removed; search stays vector-only ([ADR-0006](./adr/0006-keyword-leg-tried-not-adopted.md))

**Known limits (not shipped):**

- 75 questions: one question moves Recall@1 by 1.3 points; the two label policies are not directly comparable (README)
- Not in CI: the run needs Docker, the corpus download and an embedding model
- Page-level labels only; no passage-level relevance

**Rules:** [README § Retrieval evaluation](../README.md#retrieval-evaluation)

---

## Phase 4 - Agentic review (first slice)

**Tag:** Product, and Skills-practice (structured LLM output, grounding).

**Problem:** `/answer` returns free text. A review needs a per-requirement judgment a client can act on, with evidence it can trust.

**Decision:** `POST /documents/{id}/review` takes a list of requirements. Each one is retrieved against the document, then Claude returns a schema-constrained verdict (`satisfied`, `not_satisfied`, `not_found`) with a rationale and passage citations. Verdicts without a real citation are downgraded ([ADR-0007](./adr/0007-review-verdicts-must-cite-real-passages.md)).

**Shipped:**

- `POST /documents/{document_id}/review` with 1-20 `requirements` and optional `limit`; returns one finding per requirement with verdict, rationale and page-cited sources
- `app.agentic_review`: `ReviewVerdict` schema, `Reviewer` protocol with a Claude implementation (`messages.parse`), and the grounding rules in `review.py`
- Same 404 for missing or foreign documents, 503 without an API key, 502 on model failure
- `python -m evals.review` from `backend/`: 18 labeled requirements over GDPR and the AI Act; first run scored 18/18 verdicts, with a labeled evidence page cited on 11 of 14 (the other 3 cited unlabeled pages, likely incomplete labels)
- Live check on the GDPR PDF: "breaches notified within 72 hours" returned `satisfied` citing Article 33 (page 52); "data is sold to third parties" returned `not_found` with no sources

**Known limits (not shipped):**

- Single turn per requirement: no multi-turn or tool-using agent, no critique loop
- Requirements are supplied by the caller; no built-in checklists
- Sequential model calls in one request; one failure fails the whole review
- The 18-requirement set is easy (no borderline cases), so 18/18 is a smoke test, not a quality claim; downgrade rate not tracked
- No frontend screen; API-only

**ADRs:** [ADR-0007: Review verdicts must cite real passages](./adr/0007-review-verdicts-must-cite-real-passages.md).

---

## Not yet started

- **Phase 4, remainder** — multi-turn or tool-using review, built-in checklists, a verdict evaluation set.
- **Phase 5+ (cloud deploy, scaling)** — see README; decisions pending.

---

## How this doc stays honest

A phase only gets an entry here once it's shipped and verified, mirroring
`skills-map.md`'s rule: this describes what exists, not what's intended.
When a new phase lands, add one entry above "Not yet started," cite the
ADR(s) that defend it, and link relevant spec sections if behavior changed.
If a decision later gets superseded, the phase entry stays as shipped-then, not
rewritten — the ADR's own Resolution/Status field is where the correction lives.
