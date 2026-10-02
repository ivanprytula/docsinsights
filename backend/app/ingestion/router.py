import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile

from app.api.deps import CurrentUser, EmbedderDep, SessionDep
from app.ingestion import crud
from app.ingestion.document_parser import (
    EncryptedDocumentError,
    UnsupportedDocumentError,
    parse_pdf,
)
from app.ingestion.models import Document, DocumentPublic, DocumentsPublic
from app.models import Message, User

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _get_visible_document(
    *, session: SessionDep, current_user: User, id: uuid.UUID
) -> Document:
    """Return the document, or 404 if missing or not the caller's (superusers see all)."""
    document = crud.get_document(session=session, id=id)
    if document is None or (
        not current_user.is_superuser and document.owner_id != current_user.id
    ):
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/", response_model=DocumentsPublic)
def read_documents(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """List documents owned by the current user."""
    documents, count = crud.list_documents_for_owner(
        session=session, owner_id=current_user.id, skip=skip, limit=limit
    )
    return DocumentsPublic(
        data=[DocumentPublic.model_validate(d) for d in documents], count=count
    )


@router.get("/{id}", response_model=DocumentPublic)
def read_document(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """Get a document by ID."""
    document = _get_visible_document(session=session, current_user=current_user, id=id)
    return document


@router.post("/upload", response_model=DocumentPublic, status_code=201)
def upload_document(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    embedder: EmbedderDep,
    file: UploadFile,
) -> Any:
    """Upload a PDF; its pages are extracted, embedded and stored as chunks."""
    if file.size is not None and file.size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is too large")
    document = Document(
        filename=file.filename or "untitled.pdf", owner_id=current_user.id
    )
    try:
        chunks = parse_pdf(file.file, doc_id=document.id)
    except EncryptedDocumentError:
        raise HTTPException(status_code=422, detail="PDF is password-protected")
    except UnsupportedDocumentError:
        raise HTTPException(status_code=422, detail="File is not a readable PDF")
    if not chunks:
        raise HTTPException(status_code=422, detail="PDF contains no extractable text")
    embeddings = embedder.embed_documents([c.text for c in chunks])
    return crud.save_document(
        session=session, document=document, chunks=chunks, embeddings=embeddings
    )


@router.delete("/{id}")
def delete_document(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """Delete a document."""
    document = _get_visible_document(session=session, current_user=current_user, id=id)
    crud.delete_document(session=session, document=document)
    return Message(message="Document deleted successfully")
