import logging
import uuid
from typing import Annotated

import anthropic
from fastapi import APIRouter, HTTPException, Path

from app.agentic_review.models import Review, ReviewRequest
from app.agentic_review.review import review_requirements
from app.api.deps import CurrentUser, EmbedderDep, ReviewerDep, SessionDep
from app.ingestion import crud as ingestion_crud
from app.retrieval.models import SearchHit
from app.retrieval.router import find_passages

logger = logging.getLogger(__name__)

router = APIRouter(tags=["review"])


@router.post("/documents/{document_id}/review", response_model=Review)
def review_document(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    embedder: EmbedderDep,
    reviewer: ReviewerDep,
    document_id: Annotated[uuid.UUID, Path()],
    body: ReviewRequest,
) -> Review:
    """Judge each requirement against the user's own document, with page-cited evidence."""

    def find_in_document(requirement: str) -> list[SearchHit]:
        return find_passages(
            session=session,
            user=current_user,
            embedder=embedder,
            query=requirement,
            limit=body.limit,
            document_id=document_id,
        )

    document = ingestion_crud.get_document(session=session, id=document_id)
    if document is None or document.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        findings = review_requirements(
            requirements=body.requirements,
            find_passages=find_in_document,
            reviewer=reviewer,
        )
    except anthropic.APIError:
        logger.exception("Document review failed")
        raise HTTPException(status_code=502, detail="Review service unavailable")
    return Review(findings=findings)
