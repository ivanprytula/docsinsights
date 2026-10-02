# ADR-0005: Embedder Lives in Ingestion; Vectors Stored in pgvector

**Status:** Accepted
**Date:** 2026-10-02
**Deciders:** Ivan

## Context

Phase 2 needs every uploaded chunk embedded and stored. [ADR-0003](./0003-modulith-package-seam.md) fixes the dependency direction: `retrieval` depends on `ingestion`, never the reverse. [ADR-0002](./0002-rag-stack-and-retrieval-design.md) sketched `embedder.py` under `retrieval/`, which would force `ingestion` to import `retrieval` the moment upload embeds a chunk. ADR-0002 also deferred pgvector to Phase 4, but Phase 2 still needs somewhere to put vectors.

## Decision

1. **`Embedder` and `FastEmbedEmbedder` live in `ingestion/embedder.py`.** The upload route embeds chunks and `crud.save_document` persists text and vector in one transaction. `retrieval` (Phase 3) imports the embedder from `ingestion` to embed queries, which is the allowed direction.
2. **Vectors live in `DocumentChunk.embedding`, a pgvector `vector(N)` column, `NOT NULL`.** `N` is read from fastembed's model registry (`EMBEDDING_DIMENSIONS`), with `DEFAULT_DIMENSIONS` as fallback for unlisted models. The Alembic revision freezes `N` as a literal, as migrations must.
3. **No BGE query instruction prefix.** bge-small v1.5 works without it (fastembed's model notes call it "not so necessary"); the gain is unmeasured on our data. The prefix only affects query vectors, so adding it later needs no re-embedding.
4. **Postgres image is `pgvector/pgvector:pg18`** in compose and CI. The migration runs `CREATE EXTENSION IF NOT EXISTS vector`.

## Options Considered

| Option | Verdict |
| --- | --- |
| Embedder in `retrieval`, called from ingestion | Rejected: reverses the ADR-0003 dependency. |
| Embedder in `ingestion`, `retrieval` imports it | **Chosen.** Ingestion owns the vector column, so it owns the model that fills it; ingest and query share one model constant by construction. |
| Protocol in `ingestion`, implementation injected from `retrieval` | Rejected: indirection with one implementation; ADR-0003 forbids abstractions without a second consumer. |
| Separate indexing step owned by `retrieval`, writing to `ingestion`'s table | Rejected: violates the "retrieval never writes ingestion's tables" rule and adds a not-yet-searchable window. |
| Float array column, search in Python | Rejected: no ANN index path; rewrite at Phase 3. |

## When I would change this

- **Embedding becomes the upload bottleneck** (large PDFs block the request): move embedding to a background worker; the chunk row is then inserted without a vector, so the `NOT NULL` constraint is relaxed in that same change.
- **A second embedding model is needed** (e.g. A/B or domain-specific): the column dimension is baked into the schema, so add a second column or a `chunk_embedding` table keyed by model instead of altering this one.
- **A query-prefix eval shows a gain** (prefix vs. none on real PDFs): add the prefix inside `embed_query`; stored vectors are unaffected.
- **Retrieval needs to write derived data** (e.g. reranker caches): give it its own tables in `retrieval/models.py`.

## Consequences

- Swapping the model means a migration plus re-embedding every chunk; `EMBEDDING_DIMENSIONS` changing without a migration fails loudly at insert.
- Upload latency now includes embedding (CPU). The model loads on first upload, not at startup.
- Local dev DB volume must be compatible with the pgvector image; CI uses the same image.
- No ANN index yet; added with search in Phase 3.
