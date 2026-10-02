from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, EmbedderDep, SessionDep
from app.ingestion import crud as ingestion_crud
from app.retrieval.models import SearchRequest, SearchResults
from app.retrieval.search import find_similar_chunks

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResults)
def search_documents(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    embedder: EmbedderDep,
    body: SearchRequest,
) -> SearchResults:
    """Find passages closest to a query in the current user's documents (or one of them)."""
    if body.document_id is not None:
        document = ingestion_crud.get_document(session=session, id=body.document_id)
        if document is None or document.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Document not found")
    hits = find_similar_chunks(
        session=session,
        owner_id=current_user.id,
        query_embedding=embedder.embed_query(body.query),
        limit=body.limit,
        document_id=body.document_id,
    )
    return SearchResults(data=hits, count=len(hits))
