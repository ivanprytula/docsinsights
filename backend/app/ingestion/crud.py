import uuid

from sqlmodel import Session, col, func, select

from app.ingestion.document_parser import Chunk
from app.ingestion.models import Document, DocumentChunk


def save_document(
    *,
    session: Session,
    document: Document,
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> Document:
    """Persist a document and its embedded page chunks in one transaction."""
    session.add(document)
    session.add_all(
        DocumentChunk(
            document_id=document.id,
            page_num=c.page_num,
            text=c.text,
            embedding=embedding,
        )
        for c, embedding in zip(chunks, embeddings, strict=True)
    )
    session.commit()
    session.refresh(document)
    return document


def get_document(*, session: Session, id: uuid.UUID) -> Document | None:
    return session.get(Document, id)


def list_documents_for_owner(
    *, session: Session, owner_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> tuple[list[Document], int]:
    count_statement = (
        select(func.count()).select_from(Document).where(Document.owner_id == owner_id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(Document)
        .where(Document.owner_id == owner_id)
        .order_by(col(Document.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    documents = session.exec(statement).all()
    return list(documents), count


def delete_document(*, session: Session, document: Document) -> None:
    session.delete(document)
    session.commit()
