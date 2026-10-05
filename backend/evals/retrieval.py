import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app import crud as user_crud
from app.ingestion import crud as ingestion_crud
from app.ingestion.document_parser import parse_pdf
from app.ingestion.embedder import Embedder
from app.ingestion.models import Document
from app.models import UserCreate
from app.retrieval.search import find_similar_chunks
from evals.metrics import bootstrap_interval, mean_reciprocal_rank, recall_at_k

EVALS_DIR = Path(__file__).resolve().parent
KS = (1, 3, 5)
SHOWN_HITS = 3


class EvalQuestion(BaseModel):
    """A question and where its answer lives: one document, one or more pages."""

    model_config = ConfigDict(frozen=True)

    question: str = Field(min_length=1)
    document: str = Field(min_length=1)
    pages: list[int] = Field(min_length=1)


class QuestionResult(BaseModel):
    question: str
    first_rank: int | None
    top_hits: list[tuple[str, int, float]]


class EvalReport(BaseModel):
    results: list[QuestionResult]

    @property
    def ranks(self) -> list[int | None]:
        return [r.first_rank for r in self.results]

    def recall(self, k: int) -> float:
        return recall_at_k(self.ranks, k)

    def mrr(self) -> float:
        return mean_reciprocal_rank(self.ranks)

    def recall_interval(self, k: int) -> tuple[float, float]:
        return bootstrap_interval(self.ranks, lambda ranks: recall_at_k(ranks, k))

    def mrr_interval(self) -> tuple[float, float]:
        return bootstrap_interval(self.ranks, mean_reciprocal_rank)


def load_questions(path: Path) -> list[EvalQuestion]:
    """Read the golden set: a JSON list of {question, document, pages}."""
    return [EvalQuestion.model_validate(item) for item in json.loads(path.read_text())]


def ingest_corpus(
    *, session: Session, embedder: Embedder, owner_id: uuid.UUID, pdf_paths: list[Path]
) -> int:
    """Parse, embed and store each PDF as the owner's document; returns chunk count."""
    total = 0
    for path in pdf_paths:
        document = Document(filename=path.name, owner_id=owner_id)
        with path.open("rb") as file:
            chunks = parse_pdf(file, doc_id=document.id)
        embeddings = embedder.embed_documents([c.text for c in chunks])
        ingestion_crud.save_document(
            session=session, document=document, chunks=chunks, embeddings=embeddings
        )
        total += len(chunks)
    return total


def evaluate(
    *,
    session: Session,
    embedder: Embedder,
    owner_id: uuid.UUID,
    questions: list[EvalQuestion],
) -> EvalReport:
    """Run every question through search and record where its answer ranked."""
    results = []
    for q in questions:
        hits = find_similar_chunks(
            session=session,
            owner_id=owner_id,
            query_embedding=embedder.embed_query(q.question),
            limit=max(KS),
        )
        first_rank = next(
            (
                rank
                for rank, hit in enumerate(hits, start=1)
                if hit.filename == q.document and hit.page_num in q.pages
            ),
            None,
        )
        results.append(
            QuestionResult(
                question=q.question,
                first_rank=first_rank,
                top_hits=[(h.filename, h.page_num, h.score) for h in hits[:SHOWN_HITS]],
            )
        )
    return EvalReport(results=results)


def _format_interval(interval: tuple[float, float]) -> str:
    return f"[{interval[0]:.2f}-{interval[1]:.2f}]"


def save_report(report: EvalReport, *, chunk_count: int, path: Path) -> None:
    """Write the run as JSON so two runs can be compared question by question."""
    record = {
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "chunk_count": chunk_count,
        "recall": {str(k): report.recall(k) for k in KS},
        "mrr": report.mrr(),
        "results": [r.model_dump() for r in report.results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2))


def format_report(report: EvalReport, *, chunk_count: int) -> str:
    lines = [f"questions: {len(report.results)}  chunks: {chunk_count}"]
    metrics = [
        f"Recall@{k} {report.recall(k):.2f} {_format_interval(report.recall_interval(k))}"
        for k in KS
    ]
    metrics.append(f"MRR {report.mrr():.2f} {_format_interval(report.mrr_interval())}")
    lines.append("  ".join(metrics))
    for r in report.results:
        rank = "-" if r.first_rank is None else str(r.first_rank)
        lines.append(f"  rank {rank:>2}  {r.question}")
        if r.first_rank != 1:
            for filename, page, score in r.top_hits:
                lines.append(f"            got {filename} p{page} ({score:.3f})")
    return "\n".join(lines)


def main() -> None:
    """Ingest the corpus into a throwaway database and print retrieval metrics."""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--corpus", type=Path, default=EVALS_DIR / "corpus")
    parser.add_argument("--questions", type=Path, default=EVALS_DIR / "questions.json")
    parser.add_argument(
        "--output",
        type=Path,
        default=EVALS_DIR / "results" / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json",
        help="where to save the run as JSON (default: evals/results/<timestamp>.json)",
    )
    args = parser.parse_args()

    # Imported here: starting the throwaway database must precede building the engine.
    from tests.utils.database import start_test_database, stop_test_database

    start_test_database()
    try:
        from app.core.db import engine
        from app.ingestion.embedder import FastEmbedEmbedder

        embedder = FastEmbedEmbedder()
        with Session(engine) as session:
            owner = user_crud.create_user(
                session=session,
                user_create=UserCreate(
                    email="eval@example.com", password="eval-password-123"
                ),
            )
            chunk_count = ingest_corpus(
                session=session,
                embedder=embedder,
                owner_id=owner.id,
                pdf_paths=sorted(args.corpus.glob("*.pdf")),
            )
            report = evaluate(
                session=session,
                embedder=embedder,
                owner_id=owner.id,
                questions=load_questions(args.questions),
            )
        save_report(report, chunk_count=chunk_count, path=args.output)
        print(format_report(report, chunk_count=chunk_count))  # noqa: T201 - CLI output
        print(f"saved: {args.output}")  # noqa: T201 - CLI output
    finally:
        stop_test_database()


if __name__ == "__main__":
    main()
