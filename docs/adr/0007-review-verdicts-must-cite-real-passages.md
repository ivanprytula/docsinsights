# ADR-0007: Review Verdicts Must Cite Real Passages

**Status:** Accepted
**Date:** 2026-10-05
**Deciders:** Ivan

## Context

`POST /documents/{id}/review` asks Claude to judge a requirement against retrieved passages and return a structured verdict (`satisfied`, `not_satisfied`, `not_found`) with the numbers of the passages it relied on. Structured output guarantees the shape of the JSON, not that a citation number refers to a passage that was actually sent.

## Decision

The service keeps a verdict only if it is grounded:

- Citations outside `1..len(passages)` are dropped.
- A `satisfied` or `not_satisfied` verdict left with no valid citation becomes `not_found`.
- No passages retrieved: `not_found` without calling the model.
- Refusal or truncated output: `verdict` is `null`, distinct from `not_found` ("the document is silent" versus "the review failed").

## Options Considered

| Option | Verdict |
| --- | --- |
| Trust the model's verdict and citations as returned | Rejected: a confident verdict with a bogus page reference is the worst failure for a review tool. |
| Fail the request on an invalid citation | Rejected: one bad citation would discard the other findings. |
| Downgrade to `not_found` | **Chosen.** Never shows a finding without evidence; costs a possible false `not_found`. |

## Consequences

- Every non-null verdict other than `not_found` has at least one real page citation.
- The downgrade rate is not measured. If it is high, the prompt or the retrieval limit needs work.
- One failed model call fails the whole review (502); there is no per-finding error state.
- Requirements run sequentially in one request, which will not hold for long checklists.
