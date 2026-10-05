import uuid

from sqlmodel import Session, col, select

from app.ingestion.models import Document, DocumentChunk
from app.retrieval.models import SearchHit


def find_similar_chunks(
    *,
    session: Session,
    owner_id: uuid.UUID,
    query_embedding: list[float],
    limit: int,
    document_id: uuid.UUID | None = None,
) -> list[SearchHit]:
    """Return the owner's chunks nearest to the query by cosine distance.

    With `document_id`, only that document is searched.
    """
    # pgvector adds cosine_distance via the column type's comparator; type checkers can't see it.
    distance = col(DocumentChunk.embedding).cosine_distance(query_embedding)  # ty: ignore[unresolved-attribute]
    statement = (
        select(DocumentChunk, Document.filename, distance.label("distance"))
        .join(Document, col(Document.id) == col(DocumentChunk.document_id))
        .where(Document.owner_id == owner_id)
        .order_by(distance)
        .limit(limit)
    )
    if document_id is not None:
        statement = statement.where(Document.id == document_id)
    return [
        SearchHit(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            filename=filename,
            page_num=chunk.page_num,
            text=chunk.text,
            score=1 - distance_value,
        )
        for chunk, filename, distance_value in session.exec(statement)
    ]
