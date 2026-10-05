import logging
import uuid

import anthropic
from fastapi import APIRouter, HTTPException
from sqlmodel import Session

from app.api.deps import AnswererDep, CurrentUser, EmbedderDep, SessionDep
from app.ingestion import crud as ingestion_crud
from app.ingestion.embedder import Embedder
from app.models import User
from app.retrieval.models import (
    Answer,
    AnswerRequest,
    AnswerSource,
    SearchHit,
    SearchRequest,
    SearchResults,
)
from app.retrieval.search import find_similar_chunks

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


def _find_passages(
    *,
    session: Session,
    user: User,
    embedder: Embedder,
    query: str,
    limit: int,
    document_id: uuid.UUID | None,
) -> list[SearchHit]:
    """Search the user's own passages; a missing or foreign document is a 404."""
    if document_id is not None:
        document = ingestion_crud.get_document(session=session, id=document_id)
        if document is None or document.owner_id != user.id:
            raise HTTPException(status_code=404, detail="Document not found")
    return find_similar_chunks(
        session=session,
        owner_id=user.id,
        query_embedding=embedder.embed_query(query),
        limit=limit,
        document_id=document_id,
    )


@router.post("/search", response_model=SearchResults)
def search_documents(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    embedder: EmbedderDep,
    body: SearchRequest,
) -> SearchResults:
    """Find passages closest to a query in the current user's documents (or one of them)."""
    hits = _find_passages(
        session=session,
        user=current_user,
        embedder=embedder,
        query=body.query,
        limit=body.limit,
        document_id=body.document_id,
    )
    return SearchResults(data=hits, count=len(hits))


@router.post("/answer", response_model=Answer)
def answer_question(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    embedder: EmbedderDep,
    answerer: AnswererDep,
    body: AnswerRequest,
) -> Answer:
    """Answer a question from the user's own passages, citing them as [n] in `sources` order."""
    hits = _find_passages(
        session=session,
        user=current_user,
        embedder=embedder,
        query=body.question,
        limit=body.limit,
        document_id=body.document_id,
    )
    sources = [
        AnswerSource(n=n, filename=h.filename, page_num=h.page_num, text=h.text)
        for n, h in enumerate(hits, start=1)
    ]
    if not hits:
        return Answer(answer=None, sources=sources)
    try:
        text = answerer.answer(question=body.question, passages=hits)
    except anthropic.APIError:
        logger.exception("Answer generation failed")
        raise HTTPException(status_code=502, detail="Answer service unavailable")
    return Answer(answer=text, sources=sources)
