# ADR-0002: RAG Stack and Retrieval Design

**Status:** Accepted
**Date:** 2026-09-28
**Deciders:** Ivan

## Context

DocsInsights Phase 2–4 requires a document ingestion and retrieval pipeline to power semantic search and agentic Q&A over PDF/DOCX files with citations. Key constraints: portfolio scope (single backend), offline-first operation where feasible, and explicit (not black-box) retrieval logic.

## Decision

### Embedding Model: fastembed (lightweight, CPU-optimized)

**Why:** Fastembed is ~100MB, CPU-friendly, no GPU needed. On modest hardware (older laptops without GPU), it's the right choice. sentence-transformers (1GB+) is overkill for Phase 2 and won't run efficiently without acceleration. fastembed's default model (BAAI/bge-small-en-v1.5) is adequate for retrieval re-ranking.

**Trade-off:** Fewer pre-trained model options than sentence-transformers; locked into fastembed's ecosystem. If quality degrades, Phase 2b/3 can swap to a larger model behind an `Embedder` interface (no retrieval logic change).

### Ingestion Scope: PDF only (Phase 2)

**Why:** PDF parsing is mature (pypdf); no OCR complexity. DOCX parsing (python-docx) deferred to Phase 3 once PDF pipeline is proven. Chunking strategy and citation logic apply equally to both.

**Trade-off:** Limits initial use cases; accelerates MVP. Users uploading DOCX files will fail fast with clear messaging, not silently corrupt.

### Page/Chunk Granularity: Metadata from pypdf, simplest approach

**Why:** pypdf extracts `page_num` from each page during parsing. Store page metadata alongside chunks; retrieve it at query time. No manual page-number mapping or approximation.

**Trade-off:** Citations ground to *pages*, not *exact sentences*. Users see "found on page 5"; LLM must cite the specific passage. This is acceptable for MVP; exact-span grounding is Phase 4.

### Re-ranking: Cross-encoder (threshold TBD)

**Why:** Hybrid search (BM25 + dense embedding) produces many candidates; re-rank by semantic relevance before LLM. Cross-encoder models (cross-encoder/ms-marco-MiniLM-L-6-v2) give a [0, 1] relevance score without training.

**Threshold:** Defer until retrieval pipeline ships. Start with top-k (e.g., top 5 re-ranked results) and tune based on quality. If score distribution looks uniform, raise k; if outliers dominate, set a score floor (e.g., ≥ 0.5).

## Implementation Sketch

```
ingestion/
  document_parser.py       # parse_pdf(file) -> List[Chunk]
  models.py                # Chunk dataclass with (text, page_num, doc_id)

retrieval/
  embedder.py              # embed(text: str) -> np.ndarray (all-MiniLM)
  hybrid_search.py         # bm25 + semantic, combined ranking
  reranker.py              # cross-encoder score + threshold
  retriever.py             # orchestrate: parse -> embed -> bm25 -> dense -> rerank

agentic_review/
  qa_chain.py              # LangGraph: query -> retrieve -> ground -> generate
  prompts.py               # System prompt for citation discipline
```

Storage: SQLite (dev) with `documents` (id, filename, content, embeddings) and `chunks` (doc_id, page_num, text, embedding). PostgreSQL in production.

## When I would change this

- **Embedding model:** If latency or quality degrades in Phase 2b/3, swap to sentence-transformers or a larger model behind an `Embedder` interface. No code change in retrieval logic (interface abstraction protects against swaps). Phase 4–5: domain-specific models (legal embedding, medical embedding) plugged in the same way.
- **Ingestion scope:** Add DOCX when PDF pipeline is stable and users request it. Phase 2b: add vision/handwritten via OCR.
- **Granularity:** If citations must be more precise than "page N," add span-level grounding (sentence boundaries or LLM-extracted passages) in Phase 4.
- **Re-ranking:** If threshold tuning shows misses (good docs filtered out), lower it; if noise (bad docs ranked high), raise it. Phase 4: switch to a domain-specific re-ranker or fine-tune cross-encoder on labeled data.
- **Storage:** SQLite (Phase 2–3) → PostgreSQL + PGVector (Phase 4) for vector persistence at scale. *Superseded in part by [ADR-0005](./0005-embedder-ownership-and-pgvector-storage.md): pgvector from Phase 2, and the embedder lives in `ingestion/`.*

## Consequences

- Offline-first: no embedding API cost, works without internet.
- Simple MVP: focus on retrieval + citation discipline, not state-of-the-art ranking.
- Clear failure modes: unsupported formats fail fast; threshold tuning is observable.
