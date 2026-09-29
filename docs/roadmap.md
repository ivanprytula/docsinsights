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

## Not yet started

- **Phase 2 (document ingestion & vectorization)** — RAG pipeline, embedding
  models, async job queues; no ADRs yet because no decisions have been made.
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
