import json
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlmodel import Session

from app import crud as user_crud
from app.models import UserCreate
from evals.retrieval import (
    EvalQuestion,
    evaluate,
    format_report,
    ingest_corpus,
    load_questions,
    save_report,
)
from tests.utils.embedder import KeywordEmbedder
from tests.utils.pdf import make_pdf_bytes


@pytest.fixture
def owner_id(db: Session) -> uuid.UUID:
    user = user_crud.create_user(
        session=db,
        user_create=UserCreate(
            email=f"eval-{uuid.uuid4()}@example.com", password="eval-password-123"
        ),
    )
    return user.id


@pytest.fixture
def corpus(tmp_path: Path) -> list[Path]:
    policies = tmp_path / "policies.pdf"
    policies.write_bytes(
        make_pdf_bytes(["Sunny weather all week", "Refund within 14 days"])
    )
    billing = tmp_path / "billing.pdf"
    billing.write_bytes(make_pdf_bytes(["Each invoice is due in 30 days"]))
    return [policies, billing]


def test_ingest_corpus_stores_one_chunk_per_short_page(
    db: Session, owner_id: uuid.UUID, corpus: list[Path]
) -> None:
    count = ingest_corpus(
        session=db, embedder=KeywordEmbedder(), owner_id=owner_id, pdf_paths=corpus
    )

    assert count == 3


def test_evaluate_ranks_the_expected_page_first_when_search_finds_it(
    db: Session, owner_id: uuid.UUID, corpus: list[Path]
) -> None:
    embedder = KeywordEmbedder()
    ingest_corpus(session=db, embedder=embedder, owner_id=owner_id, pdf_paths=corpus)
    questions = [
        EvalQuestion(question="refund", document="policies.pdf", pages=[2]),
        EvalQuestion(question="invoice", document="billing.pdf", pages=[1]),
    ]

    report = evaluate(
        session=db, embedder=embedder, owner_id=owner_id, questions=questions
    )

    assert report.ranks == [1, 1]
    assert report.recall(1) == 1.0
    assert report.mrr() == 1.0


def test_evaluate_ranks_a_less_similar_expected_page_below_the_best_match(
    db: Session, owner_id: uuid.UUID, corpus: list[Path]
) -> None:
    embedder = KeywordEmbedder()
    ingest_corpus(session=db, embedder=embedder, owner_id=owner_id, pdf_paths=corpus)
    question = EvalQuestion(question="refund", document="policies.pdf", pages=[1])

    report = evaluate(
        session=db, embedder=embedder, owner_id=owner_id, questions=[question]
    )

    assert report.ranks[0] is not None
    assert report.ranks[0] > 1


def test_evaluate_reports_none_when_the_expected_page_does_not_exist(
    db: Session, owner_id: uuid.UUID, corpus: list[Path]
) -> None:
    embedder = KeywordEmbedder()
    ingest_corpus(session=db, embedder=embedder, owner_id=owner_id, pdf_paths=corpus)
    question = EvalQuestion(question="refund", document="policies.pdf", pages=[99])

    report = evaluate(
        session=db, embedder=embedder, owner_id=owner_id, questions=[question]
    )

    assert report.ranks == [None]
    assert report.recall(5) == 0.0


def test_format_report_lists_top_hits_only_for_questions_not_ranked_first(
    db: Session, owner_id: uuid.UUID, corpus: list[Path]
) -> None:
    embedder = KeywordEmbedder()
    ingest_corpus(session=db, embedder=embedder, owner_id=owner_id, pdf_paths=corpus)
    questions = [
        EvalQuestion(question="refund", document="policies.pdf", pages=[2]),
        EvalQuestion(question="invoice", document="policies.pdf", pages=[1]),
    ]

    report = evaluate(
        session=db, embedder=embedder, owner_id=owner_id, questions=questions
    )
    text = format_report(report, chunk_count=3)

    assert "Recall@1 0.50" in text
    assert text.count("got ") >= 1
    assert "rank  1  refund" in text


def test_load_questions_reads_the_golden_set(tmp_path: Path) -> None:
    path = tmp_path / "questions.json"
    path.write_text(
        json.dumps([{"question": "Q?", "document": "a.pdf", "pages": [1, 2]}])
    )

    assert load_questions(path) == [
        EvalQuestion(question="Q?", document="a.pdf", pages=[1, 2])
    ]


def test_load_questions_rejects_a_question_without_expected_pages(
    tmp_path: Path,
) -> None:
    path = tmp_path / "questions.json"
    path.write_text(json.dumps([{"question": "Q?", "document": "a.pdf", "pages": []}]))

    with pytest.raises(ValidationError):
        load_questions(path)


def test_save_report_writes_metrics_and_per_question_ranks(
    db: Session, owner_id: uuid.UUID, corpus: list[Path], tmp_path: Path
) -> None:
    embedder = KeywordEmbedder()
    ingest_corpus(session=db, embedder=embedder, owner_id=owner_id, pdf_paths=corpus)
    question = EvalQuestion(question="refund", document="policies.pdf", pages=[2])
    report = evaluate(
        session=db, embedder=embedder, owner_id=owner_id, questions=[question]
    )
    path = tmp_path / "runs" / "run.json"

    save_report(report, chunk_count=3, path=path)

    saved = json.loads(path.read_text())
    assert saved["chunk_count"] == 3
    assert saved["recall"]["1"] == 1.0
    assert saved["results"][0]["question"] == "refund"
    assert saved["results"][0]["first_rank"] == 1


def test_format_report_shows_a_confidence_interval_per_metric(
    db: Session, owner_id: uuid.UUID, corpus: list[Path]
) -> None:
    embedder = KeywordEmbedder()
    ingest_corpus(session=db, embedder=embedder, owner_id=owner_id, pdf_paths=corpus)
    question = EvalQuestion(question="refund", document="policies.pdf", pages=[2])
    report = evaluate(
        session=db, embedder=embedder, owner_id=owner_id, questions=[question]
    )

    text = format_report(report, chunk_count=3)

    assert "Recall@1 1.00 [1.00-1.00]" in text
    assert "MRR 1.00 [1.00-1.00]" in text
