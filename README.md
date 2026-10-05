# docsinsights

**Updated:** 2026-10-02

Document ingestion and semantic search with page-level citations, built to be measured: a retrieval evaluation harness runs over EU regulatory text (GDPR and the AI Act). Backend-first modular monolith; agentic review is planned.

Built on [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template); see [LICENSE](./LICENSE) for attribution.

## Stack

| Layer | Tech |
| --- | --- |
| Backend | FastAPI, SQLModel, PostgreSQL, Alembic |
| Frontend | React, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Auth | JWT (login + email recovery) — role/permission authz in progress |
| Infra | Docker Compose, Traefik |
| Email (dev) | Mailpit |
| Testing | pytest (backend), Playwright (e2e) |
| Package manager (frontend) | Bun (workspaces: `frontend`, `packages/*`) |

## Local Services

| Service | URL |
| --- | --- |
| Frontend (Vite dev) | <http://localhost:5173> |
| Backend API | <http://localhost:8000> |
| API docs | <http://localhost:8000/docs> |
| Traefik dashboard | <http://localhost:8090/dashboard/> |
| Adminer | <http://localhost:8080> |
| Mailpit | <http://localhost:8025> |

## Running Locally

```sh
docker compose up -d
bun install
bun run --filter frontend dev
```

Backend runs in Docker automatically. See [development.md](./development.md) for local-only mode.

## Documentation

| Doc | Covers |
| --- | --- |
| [backend/README.md](./backend/README.md) | Backend setup, structure, conventions |
| [frontend/README.md](./frontend/README.md) | Frontend setup, structure, conventions |
| [development.md](./development.md) | Local dev workflow, `.env` config, Docker Compose services |
| [deployment-docker-compose.md](./deployment-docker-compose.md) | Self-hosted deployment |
| [docs/roadmap.md](./docs/roadmap.md) | Phase breakdown and planned work |
| [docs/c4-architecture.md](./docs/c4-architecture.md) | C4 context, containers and backend components; RAG walkthrough; dependency rules |
| [docs/skills-map.md](./docs/skills-map.md) | Capability coverage by domain |
| [docs/adr/](./docs/adr/) | Architecture Decision Records |

## Status

| Phase | State |
| --- | --- |
| 1 - Auth and user identity | Shipped |
| 2 - PDF ingestion and vectorization (chunking, bge-small embeddings, pgvector) | Shipped |
| 3 - Semantic search (`POST /search`, owner-scoped, optional single document) | Shipped, vector-only |
| Retrieval evaluation harness (Recall@k, MRR) | Shipped, baseline below |
| Keyword leg (hybrid search) | Tried, not adopted: no measured gain ([ADR-0006](./docs/adr/0006-keyword-leg-tried-not-adopted.md)) |
| 4 - Agentic review (LLM answers with citations) | Planned |

Scope today: English text PDFs; no OCR; the API has no upload or search screen yet. Details in [docs/roadmap.md](./docs/roadmap.md).

## Retrieval evaluation

The harness ingests PDFs into a throwaway pgvector container, runs a golden set of questions through the real search, and reports whether the expected page ranked in the top 1, 3 and 5.

| Corpus | Source |
| --- | --- |
| `gdpr.pdf` - Regulation (EU) 2016/679 | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng) |
| `eu-ai-act.pdf` - Regulation (EU) 2024/1689 | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng) |

Texts are reused from EUR-Lex under its [legal notice](https://eur-lex.europa.eu/content/legal-notice/legal-notice.html) (credit given, no changes). The PDFs are not stored in this repo; download them into `backend/evals/corpus/` under those filenames.

```sh
cd backend && uv run python -m evals.retrieval
# review verdicts (needs ANTHROPIC_API_KEY): uv run python -m evals.review
```

**What the numbers mean.** Each question is labeled with the page(s) that answer it. A question counts as found if *any one* labeled page appears in the top k search results.

| Metric | Meaning |
| --- | --- |
| Recall@k | Share of questions with a correct page in the top k results. Recall@5 0.65 = 65 of 100 questions find their page in the top 5. |
| MRR | Average of 1/rank of the first correct page (1, 1/2, 1/3, ...; 0 if missing). Higher means the right page sits nearer the top. |
| `[low-high]` | 95% bootstrap interval. With few questions the true score can sit anywhere in it, so a difference smaller than the interval is noise. |

Baseline, vector-only search (786 chunks):

| Question set | n | Recall@1 | Recall@3 | Recall@5 | MRR |
| --- | --- | --- | --- | --- | --- |
| All | 75 | 0.33 [0.24-0.45] | 0.52 | 0.65 [0.55-0.76] | 0.45 [0.36-0.55] |
| Original questions (recitals accepted) | 28 | 0.50 | 0.64 | 0.71 | 0.58 |
| Added questions (operative articles only) | 47 | 0.23 | 0.45 | 0.62 | 0.37 |

**The two rows are not directly comparable.** Labels for the original 28 come from the article that answers the question plus any recital that directly addresses the topic. Labels for the 47 added questions come from the article's page span only; a recital that answers the question is scored as a miss. Of the 36 added questions not ranked first, 26 have a recital page as the top hit, so the added row probably understates retrieval quality (I did not check each recital). A recital review that would unify the labels was dropped as not worth the effort at this stage. Spans come from the PDF headings, never from search results.

Each run is saved as JSON under `backend/evals/results/` (gitignored); `--output <path>` picks the file. A keyword search leg was tried against the earlier 28-question set and did not help ([ADR-0006](./docs/adr/0006-keyword-leg-tried-not-adopted.md)).

History: the first run (22 plain-language questions, operative-page labels only) scored Recall@1 0.27, Recall@5 0.68. The labels were then broadened to the original policy after many misses turned out to be adjacent pages or recitals, and 6 exact-reference questions were added. 47 more questions followed to narrow the intervals.

Needs Docker running. Questions live in `backend/evals/questions.json` as `{question, document, pages}`; pages are PDF page indexes. Not legal advice: this is a retrieval demo over public texts.

## License

MIT — see [LICENSE](./LICENSE).
