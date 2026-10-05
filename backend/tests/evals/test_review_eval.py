import json
import uuid
from collections.abc import Sequence
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlmodel import Session

from app import crud as user_crud
from app.agentic_review.models import ReviewVerdict, Verdict
from app.models import UserCreate
from app.retrieval.models import SearchHit
from evals.retrieval import EVALS_DIR, ingest_corpus
from evals.review import (
    EvalRequirement,
    RequirementResult,
    ReviewEvalReport,
    evaluate_reviews,
    format_review_report,
    load_requirements,
    save_review_report,
)
from tests.utils.embedder import KeywordEmbedder
from tests.utils.pdf import make_pdf_bytes


class CitingReviewer:
    """Says `satisfied` for every requirement and cites the first passage."""

    def review(
        self, *, requirement: str, passages: Sequence[SearchHit]
    ) -> ReviewVerdict | None:
        return ReviewVerdict(verdict=Verdict.SATISFIED, rationale="r", citations=[1])


@pytest.fixture
def owner_id(db: Session) -> uuid.UUID:
    user = user_crud.create_user(
        session=db,
        user_create=UserCreate(
            email=f"eval-{uuid.uuid4()}@example.com", password="eval-password-123"
        ),
    )
    return user.id


def _result(
    expected: Verdict, got: Verdict | None, *, evidence_cited: bool = False
) -> RequirementResult:
    return RequirementResult(
        requirement="R",
        expected=expected,
        got=got,
        cited_pages=[],
        evidence_cited=evidence_cited,
    )


def test_shipped_requirement_set_is_valid_and_covers_every_verdict() -> None:
    items = load_requirements(EVALS_DIR / "review_requirements.json")

    assert {i.expected for i in items} == set(Verdict)
    for item in items:
        assert (item.expected == Verdict.NOT_FOUND) == (item.pages == [])


def test_requirement_rejects_an_unknown_verdict() -> None:
    with pytest.raises(ValidationError):
        EvalRequirement.model_validate(
            {"requirement": "R", "document": "d.pdf", "expected": "maybe", "pages": []}
        )


def test_accuracy_counts_exact_verdict_matches() -> None:
    report = ReviewEvalReport(
        results=[
            _result(Verdict.SATISFIED, Verdict.SATISFIED),
            _result(Verdict.NOT_SATISFIED, Verdict.SATISFIED),
            _result(Verdict.NOT_FOUND, None),
            _result(Verdict.NOT_FOUND, Verdict.NOT_FOUND),
        ]
    )

    assert report.accuracy() == 0.5
    assert report.no_verdict_count() == 1
    assert report.confusion() == {
        "satisfied": {"satisfied": 1},
        "not_satisfied": {"satisfied": 1},
        "not_found": {"none": 1, "not_found": 1},
    }


def test_evidence_rate_ignores_requirements_without_evidence() -> None:
    report = ReviewEvalReport(
        results=[
            _result(Verdict.SATISFIED, Verdict.SATISFIED, evidence_cited=True),
            _result(Verdict.SATISFIED, Verdict.SATISFIED, evidence_cited=False),
            _result(Verdict.NOT_FOUND, Verdict.NOT_FOUND),
        ]
    )

    assert report.evidence_rate() == 0.5


def test_evaluate_reviews_checks_cited_pages_against_labeled_pages(
    db: Session, owner_id: uuid.UUID, tmp_path: Path
) -> None:
    pdf = tmp_path / "policies.pdf"
    pdf.write_bytes(make_pdf_bytes(["Sunny weather all week", "Refund within 14 days"]))
    embedder = KeywordEmbedder()
    ingest_corpus(session=db, embedder=embedder, owner_id=owner_id, pdf_paths=[pdf])
    requirements = [
        EvalRequirement(
            requirement="refund",
            document="policies.pdf",
            expected=Verdict.SATISFIED,
            pages=[2],
        ),
        EvalRequirement(
            requirement="refund",
            document="policies.pdf",
            expected=Verdict.SATISFIED,
            pages=[1],
        ),
    ]

    report = evaluate_reviews(
        session=db,
        embedder=embedder,
        reviewer=CitingReviewer(),
        owner_id=owner_id,
        requirements=requirements,
    )

    assert [r.cited_pages for r in report.results] == [[2], [2]]
    assert [r.evidence_cited for r in report.results] == [True, False]
    assert report.accuracy() == 1.0


def test_format_and_save_list_misses_and_round_trip(tmp_path: Path) -> None:
    report = ReviewEvalReport(
        results=[
            _result(Verdict.SATISFIED, Verdict.SATISFIED, evidence_cited=True),
            _result(Verdict.NOT_SATISFIED, Verdict.NOT_FOUND),
        ]
    )
    path = tmp_path / "out" / "review.json"

    save_review_report(report, path=path)

    text = format_review_report(report)
    assert "accuracy 0.50" in text
    assert "expected not_satisfied, got not_found" in text
    assert json.loads(path.read_text())["accuracy"] == 0.5
