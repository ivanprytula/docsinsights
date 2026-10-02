import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from app.ingestion.embedder import EMBEDDING_DIMENSIONS


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


class DocumentBase(SQLModel):
    filename: str = Field(min_length=1, max_length=255)


class DocumentCreate(DocumentBase):
    pass


class Document(DocumentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class DocumentChunk(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    document_id: uuid.UUID = Field(
        foreign_key="document.id", nullable=False, ondelete="CASCADE", index=True
    )
    page_num: int
    text: str
    embedding: list[float] = Field(
        sa_column=Column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    )


class DocumentPublic(DocumentBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class DocumentsPublic(SQLModel):
    data: list[DocumentPublic]
    count: int
