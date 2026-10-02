import uuid

from sqlmodel import Field, SQLModel


class SearchRequest(SQLModel):
    query: str = Field(min_length=1, max_length=1000)
    document_id: uuid.UUID | None = None
    limit: int = Field(default=5, ge=1, le=20)


class SearchHit(SQLModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page_num: int
    text: str
    score: float


class SearchResults(SQLModel):
    data: list[SearchHit]
    count: int
