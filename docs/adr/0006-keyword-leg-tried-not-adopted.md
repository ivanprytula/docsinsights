# ADR-0006: Keyword Leg Tried and Not Adopted; Search Stays Vector-Only

**Status:** Accepted
**Date:** 2026-10-05
**Deciders:** Ivan

## Context

[ADR-0002](./0002-rag-stack-and-retrieval-design.md) planned hybrid search. The evaluation set showed the motivating weakness: exact-reference questions ("What does Article 33 require?") scored Recall@1 0.33 against 0.55 for plain-language ones. A keyword leg was built and judged against the vector-only baseline on the same 28 questions and 786 chunks.

## What was built (then removed)

- `documentchunk.text_search`: a generated, stored `tsvector` (`to_tsvector('english', text)`) with a GIN index, via migration.
- `find_keyword_chunks`: query terms OR'd (`plainto_tsquery`, `&` swapped for `|`), ranked by `ts_rank_cd`.
- `fuse_rankings`: reciprocal rank fusion (k=60) over 50 candidates per leg.
- `find_relevant_chunks`: runs both legs and fuses them. The eval harness had a `--hybrid` flag to run it.

## Result

| Search | Recall@1 | Recall@3 | Recall@5 | MRR |
| --- | --- | --- | --- | --- |
| Vector-only | 0.50 [0.32-0.68] | 0.64 | 0.71 [0.54-0.86] | 0.58 [0.41-0.74] |
| Hybrid | 0.32 [0.14-0.50] | 0.61 | 0.64 [0.46-0.82] | 0.46 [0.31-0.62] |

Intervals are 95% bootstrap over questions. They overlap, so hybrid is not shown to be worse; it is not shown to be better, and the per-question picture leans negative: 5 questions improved, 8 got worse, 15 unchanged. Two questions fell out of the top 5 entirely.

- **Improved:** DPIA, consent withdrawal, high-risk AI obligations, general-purpose AI models, "Article 33" (rank 5 to 3).
- **Worse:** mostly plain-language questions vector search already ranked first (deletion right, DPO, chatbot disclosure). "Annex IV", an exact reference the leg was meant to help, went from 1 to 3.

## Decision

**`/search` and `/answer` stay vector-only, and the experiment is removed.** The migration (never applied to the development database), the `text_search` column, the GIN index, the keyword and fusion functions, their tests and the `--hybrid` flag were deleted. The design above is enough to rebuild it; the git history of the working branch does not keep it because it was never committed.

## Likely cause (not verified)

`ts_rank_cd` has no inverse-document-frequency weighting. In a regulation corpus, words such as "personal", "data" and "controller" occur on most pages, so OR-ing a question's terms fills the keyword ranking with generic matches. Fusion then promotes them over the correct vector hit. No experiment here confirmed this.

## Options Considered

| Option | Verdict |
| --- | --- |
| Ship hybrid as built | Rejected: no measured gain, net negative per question. |
| Lower weight for the keyword leg in fusion | Open. Cheap, but with 28 questions any weight is tuned to the set. |
| Keyword leg only for exact-reference queries (`Article \d+`, `Annex [IVX]+`) | Open. Targets the observed weakness; a heuristic, not general. |
| BM25-style ranking with term rarity | Open. The principled fix; Postgres full-text search does not provide it natively, so it means an extension or ranking in Python. |
| Keep the code and index unused | Rejected: an unused GIN index costs storage and insert time on every chunk. |
| Remove the keyword code | **Chosen.** |

## When I would change this

- **The set grows to 60-100 questions:** the current intervals span about 35 points, too wide to rank close variants. Re-measure the baseline, then try a rarity-aware or exact-reference-only variant.
- **A variant beats the baseline** by more than the interval width: add the column and index back with a migration, wire it into the router, and record the numbers in a new ADR.

## Consequences

- Exact-reference questions remain the weakest category.
- The numbers in the Result table are not reproducible from the repository any more; they are recorded here as the measurement.
