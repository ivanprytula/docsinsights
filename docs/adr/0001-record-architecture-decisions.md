# ADR-0001: Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Solo project

## Context

DocsInsights carries deliberate over-scope for a solo portfolio project (RAG pipeline, modulith seams, planned scaling). The owner must be able to defend every line in an interview — including three months from now, having forgotten why a choice was made.

## Decision

Significant decisions get an ADR in `docs/adr/`, numbered sequentially, never deleted — superseded ADRs are marked `Superseded by ADR-NNNN` and kept.

An ADR is warranted when a choice is:

- expensive to reverse (embedding model, storage engine, package seam), or
- non-obvious to a reader (why fastembed over sentence-transformers), or
- deliberately deferred for a documented reason (why async sessions wait until Phase 5).

Every ADR includes a **"When I would change this"** section. No stated reversal condition means it's an advertisement, not a decision.

## Consequences

Repo is self-explaining to a reviewer with 15 minutes. Cost: writing overhead per meaningful change, and risk of drift from the code — mitigated by keeping ADRs short and linking them from the roadmap/code they describe.

## When I would change this

If this project gained collaborators, ADRs would need a lightweight review step before acceptance. As a solo project, self-acceptance is fine.
