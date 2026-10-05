import uuid
from collections.abc import Sequence

from app.agentic_review.models import ReviewVerdict, Verdict
from app.agentic_review.review import review_requirement, review_requirements
from app.retrieval.models import SearchHit


def _hit(text: str, *, page: int = 1) -> SearchHit:
    return SearchHit(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename="policy.pdf",
        page_num=page,
        text=text,
        score=0.5,
    )


class FakeReviewer:
    def __init__(self, verdict: ReviewVerdict | None) -> None:
        self._verdict = verdict
        self.calls = 0

    def review(
        self, *, requirement: str, passages: Sequence[SearchHit]
    ) -> ReviewVerdict | None:
        self.calls += 1
        return self._verdict


def _verdict(kind: Verdict, citations: list[int]) -> ReviewVerdict:
    return ReviewVerdict(verdict=kind, rationale="because", citations=citations)


def test_review_requirement_maps_citations_to_pages() -> None:
    passages = [_hit("a", page=2), _hit("b", page=9)]
    finding = review_requirement(
        requirement="R",
        find_passages=lambda _: passages,
        reviewer=FakeReviewer(_verdict(Verdict.SATISFIED, [2])),
    )

    assert finding.verdict == Verdict.SATISFIED
    assert [(s.n, s.page_num, s.text) for s in finding.sources] == [(2, 9, "b")]


def test_review_requirement_drops_invented_citations() -> None:
    finding = review_requirement(
        requirement="R",
        find_passages=lambda _: [_hit("a")],
        reviewer=FakeReviewer(_verdict(Verdict.SATISFIED, [1, 7, 0])),
    )

    assert [s.n for s in finding.sources] == [1]


def test_review_requirement_downgrades_a_verdict_without_valid_citations() -> None:
    finding = review_requirement(
        requirement="R",
        find_passages=lambda _: [_hit("a")],
        reviewer=FakeReviewer(_verdict(Verdict.NOT_SATISFIED, [5])),
    )

    assert finding.verdict == Verdict.NOT_FOUND
    assert finding.sources == []


def test_review_requirement_keeps_not_found_without_citations() -> None:
    finding = review_requirement(
        requirement="R",
        find_passages=lambda _: [_hit("a")],
        reviewer=FakeReviewer(_verdict(Verdict.NOT_FOUND, [])),
    )

    assert finding.verdict == Verdict.NOT_FOUND
    assert finding.rationale == "because"


def test_review_requirement_skips_the_model_when_nothing_was_retrieved() -> None:
    reviewer = FakeReviewer(_verdict(Verdict.SATISFIED, [1]))

    finding = review_requirement(
        requirement="R", find_passages=lambda _: [], reviewer=reviewer
    )

    assert finding.verdict == Verdict.NOT_FOUND
    assert reviewer.calls == 0


def test_review_requirement_has_no_verdict_when_the_reviewer_declines() -> None:
    finding = review_requirement(
        requirement="R",
        find_passages=lambda _: [_hit("a")],
        reviewer=FakeReviewer(None),
    )

    assert finding.verdict is None
    assert finding.rationale is None


def test_review_requirements_returns_one_finding_per_requirement_in_order() -> None:
    findings = review_requirements(
        requirements=["first", "second"],
        find_passages=lambda _: [_hit("a")],
        reviewer=FakeReviewer(_verdict(Verdict.SATISFIED, [1])),
    )

    assert [f.requirement for f in findings] == ["first", "second"]
