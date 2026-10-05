import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, select

from app import crud as user_crud
from app.agentic_review.models import Verdict
from app.agentic_review.review import review_requirement
from app.agentic_review.reviewer import Reviewer
from app.ingestion.embedder import Embedder
from app.ingestion.models import Document
from app.models import UserCreate
from app.retrieval.models import SearchHit
from app.retrieval.search import find_similar_chunks
from evals.metrics import bootstrap_interval
from evals.retrieval import EVALS_DIR, ingest_corpus

PASSAGE_LIMIT = 5


class EvalRequirement(BaseModel):
    """A requirement, the verdict a careful reader gives it, and the pages that prove it."""

    model_config = ConfigDict(frozen=True)

    requirement: str = Field(min_length=1)
    document: str = Field(min_length=1)
    expected: Verdict
    pages: list[int]


class RequirementResult(BaseModel):
    requirement: str
    expected: Verdict
    got: Verdict | None
    cited_pages: list[int]
    evidence_cited: bool


class ReviewEvalReport(BaseModel):
    results: list[RequirementResult]

    def accuracy(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.got == r.expected for r in self.results) / len(self.results)

    def accuracy_interval(self) -> tuple[float, float]:
        correct: list[int | None] = [int(r.got == r.expected) for r in self.results]
        return bootstrap_interval(correct, lambda xs: sum(x or 0 for x in xs) / len(xs))

    def no_verdict_count(self) -> int:
        return sum(r.got is None for r in self.results)

    def evidence_rate(self) -> float:
        """Of the requirements that have evidence, how often a finding cited a labeled page."""
        graded = [r for r in self.results if r.expected != Verdict.NOT_FOUND]
        if not graded:
            return 0.0
        return sum(r.evidence_cited for r in graded) / len(graded)

    def confusion(self) -> dict[str, dict[str, int]]:
        """Counts of got verdict (or "none") for each expected verdict."""
        table: dict[str, dict[str, int]] = {}
        for r in self.results:
            row = table.setdefault(r.expected.value, {})
            key = r.got.value if r.got is not None else "none"
            row[key] = row.get(key, 0) + 1
        return table


def load_requirements(path: Path) -> list[EvalRequirement]:
    """Read the labeled set: a JSON list of {requirement, document, expected, pages}."""
    return [
        EvalRequirement.model_validate(item) for item in json.loads(path.read_text())
    ]


def evaluate_reviews(
    *,
    session: Session,
    embedder: Embedder,
    reviewer: Reviewer,
    owner_id: uuid.UUID,
    requirements: list[EvalRequirement],
) -> ReviewEvalReport:
    """Run each requirement through the real review path, scoped to its document."""
    document_ids = {
        d.filename: d.id
        for d in session.exec(select(Document).where(Document.owner_id == owner_id))
    }
    results = []
    for item in requirements:

        def find_in_document(
            query: str, item: EvalRequirement = item
        ) -> list[SearchHit]:
            return find_similar_chunks(
                session=session,
                owner_id=owner_id,
                query_embedding=embedder.embed_query(query),
                limit=PASSAGE_LIMIT,
                document_id=document_ids[item.document],
            )

        finding = review_requirement(
            requirement=item.requirement,
            find_passages=find_in_document,
            reviewer=reviewer,
        )
        cited_pages = [s.page_num for s in finding.sources]
        results.append(
            RequirementResult(
                requirement=item.requirement,
                expected=item.expected,
                got=finding.verdict,
                cited_pages=cited_pages,
                evidence_cited=any(p in item.pages for p in cited_pages),
            )
        )
    return ReviewEvalReport(results=results)


def _format_interval(interval: tuple[float, float]) -> str:
    return f"[{interval[0]:.2f}-{interval[1]:.2f}]"


def format_review_report(report: ReviewEvalReport) -> str:
    lines = [
        f"requirements: {len(report.results)}",
        f"accuracy {report.accuracy():.2f} {_format_interval(report.accuracy_interval())}  "
        f"evidence cited {report.evidence_rate():.2f}  no verdict {report.no_verdict_count()}",
        f"confusion (expected -> got): {json.dumps(report.confusion())}",
    ]
    for r in report.results:
        if r.got != r.expected or (
            r.expected != Verdict.NOT_FOUND and not r.evidence_cited
        ):
            got = "none" if r.got is None else r.got.value
            lines.append(
                f"  expected {r.expected.value}, got {got}, cited pages {r.cited_pages}: {r.requirement}"
            )
    return "\n".join(lines)


def save_review_report(report: ReviewEvalReport, *, path: Path) -> None:
    """Write the run as JSON so two runs can be compared requirement by requirement."""
    record = {
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "accuracy": report.accuracy(),
        "evidence_rate": report.evidence_rate(),
        "confusion": report.confusion(),
        "results": [r.model_dump(mode="json") for r in report.results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2))


def main() -> None:
    """Ingest the corpus into a throwaway database, review every labeled requirement with Claude."""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--corpus", type=Path, default=EVALS_DIR / "corpus")
    parser.add_argument(
        "--requirements", type=Path, default=EVALS_DIR / "review_requirements.json"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=EVALS_DIR
        / "results"
        / f"review-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json",
    )
    args = parser.parse_args()

    # Imported here: starting the throwaway database must precede building the engine.
    from tests.utils.database import start_test_database, stop_test_database

    start_test_database()
    try:
        from app.agentic_review.reviewer import get_reviewer
        from app.core.config import settings
        from app.core.db import engine
        from app.ingestion.embedder import FastEmbedEmbedder

        if settings.ANTHROPIC_API_KEY is None:
            raise SystemExit("ANTHROPIC_API_KEY is not set")
        embedder = FastEmbedEmbedder()
        with Session(engine) as session:
            owner = user_crud.create_user(
                session=session,
                user_create=UserCreate(
                    email="eval@example.com", password="eval-password-123"
                ),
            )
            ingest_corpus(
                session=session,
                embedder=embedder,
                owner_id=owner.id,
                pdf_paths=sorted(args.corpus.glob("*.pdf")),
            )
            report = evaluate_reviews(
                session=session,
                embedder=embedder,
                reviewer=get_reviewer(),
                owner_id=owner.id,
                requirements=load_requirements(args.requirements),
            )
        save_review_report(report, path=args.output)
        print(format_review_report(report))  # noqa: T201 - CLI output
        print(f"saved: {args.output}")  # noqa: T201 - CLI output
    finally:
        stop_test_database()


if __name__ == "__main__":
    main()
