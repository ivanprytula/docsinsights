from collections.abc import Callable, Sequence

from app.agentic_review.models import Finding, ReviewVerdict, Verdict
from app.agentic_review.reviewer import Reviewer
from app.retrieval.models import AnswerSource, SearchHit


def _cited_sources(
    verdict: ReviewVerdict, passages: Sequence[SearchHit]
) -> list[AnswerSource]:
    """Map [n] citations to passages, dropping numbers the model invented."""
    numbers = sorted({n for n in verdict.citations if 1 <= n <= len(passages)})
    return [
        AnswerSource(
            n=n,
            filename=passages[n - 1].filename,
            page_num=passages[n - 1].page_num,
            text=passages[n - 1].text,
        )
        for n in numbers
    ]


def review_requirement(
    *,
    requirement: str,
    find_passages: Callable[[str], list[SearchHit]],
    reviewer: Reviewer,
) -> Finding:
    """Retrieve passages, get a verdict, and keep it only if it cites a real passage."""
    passages = find_passages(requirement)
    if not passages:
        return Finding(
            requirement=requirement,
            verdict=Verdict.NOT_FOUND,
            rationale="No passages found.",
            sources=[],
        )
    verdict = reviewer.review(requirement=requirement, passages=passages)
    if verdict is None:
        return Finding(
            requirement=requirement, verdict=None, rationale=None, sources=[]
        )
    sources = _cited_sources(verdict, passages)
    if verdict.verdict != Verdict.NOT_FOUND and not sources:
        # A judgment with no real citation is ungrounded; treat it as not found.
        return Finding(
            requirement=requirement,
            verdict=Verdict.NOT_FOUND,
            rationale="The verdict cited no valid passage.",
            sources=[],
        )
    return Finding(
        requirement=requirement,
        verdict=verdict.verdict,
        rationale=verdict.rationale,
        sources=sources,
    )


def review_requirements(
    *,
    requirements: Sequence[str],
    find_passages: Callable[[str], list[SearchHit]],
    reviewer: Reviewer,
) -> list[Finding]:
    """Review each requirement independently, in order."""
    return [
        review_requirement(
            requirement=r, find_passages=find_passages, reviewer=reviewer
        )
        for r in requirements
    ]
