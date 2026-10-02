import io
from collections.abc import Generator, Sequence

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlmodel import Session, select

from app.core.config import settings
from app.ingestion import router as documents_router
from app.ingestion.embedder import EMBEDDING_DIMENSIONS
from app.ingestion.models import DocumentChunk
from app.ingestion.router import get_embedder
from app.main import app
from tests.utils.pdf import make_pdf_bytes


class FakeEmbedder:
    """Deterministic stand-in so API tests never load the real model."""

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.1] * EMBEDDING_DIMENSIONS for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1] * EMBEDDING_DIMENSIONS


@pytest.fixture(autouse=True)
def fake_embedder() -> Generator[None]:
    app.dependency_overrides[get_embedder] = FakeEmbedder
    yield
    app.dependency_overrides.pop(get_embedder)


UPLOAD_URL = f"{settings.API_V1_STR}/documents/upload"


def _upload(client: TestClient, headers: dict[str, str], content: bytes):
    return client.post(
        UPLOAD_URL,
        headers=headers,
        files={"file": ("sample.pdf", content, "application/pdf")},
    )


def test_upload_pdf_stores_document_and_page_chunks(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    pdf = make_pdf_bytes(["First page", "Second page"])

    r = _upload(client, normal_user_token_headers, pdf)

    assert r.status_code == 201
    body = r.json()
    assert body["filename"] == "sample.pdf"
    chunks = db.exec(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == body["id"])
        .order_by("page_num")
    ).all()
    assert [(c.page_num, c.text) for c in chunks] == [
        (1, "First page"),
        (2, "Second page"),
    ]
    assert all(len(c.embedding) == EMBEDDING_DIMENSIONS for c in chunks)


def test_upload_non_pdf_returns_422(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = _upload(client, normal_user_token_headers, b"not a pdf")

    assert r.status_code == 422
    assert r.json()["detail"] == "File is not a readable PDF"


def test_upload_password_protected_pdf_returns_422(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("secret")
    buf = io.BytesIO()
    writer.write(buf)

    r = _upload(client, normal_user_token_headers, buf.getvalue())

    assert r.status_code == 422
    assert r.json()["detail"] == "PDF is password-protected"


def test_upload_pdf_without_text_returns_422(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = _upload(client, normal_user_token_headers, make_pdf_bytes([""]))

    assert r.status_code == 422
    assert r.json()["detail"] == "PDF contains no extractable text"


def test_upload_over_size_limit_returns_413(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(documents_router, "MAX_UPLOAD_BYTES", 10)

    r = _upload(client, normal_user_token_headers, make_pdf_bytes(["too big"]))

    assert r.status_code == 413
    assert r.json()["detail"] == "File is too large"


def test_upload_requires_authentication(client: TestClient) -> None:
    r = client.post(
        UPLOAD_URL, files={"file": ("a.pdf", make_pdf_bytes(["x"]), "application/pdf")}
    )

    assert r.status_code == 401


def test_list_documents_returns_only_own_documents(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    mine = _upload(client, normal_user_token_headers, make_pdf_bytes(["mine"])).json()
    theirs = _upload(client, superuser_token_headers, make_pdf_bytes(["theirs"])).json()

    r = client.get(
        f"{settings.API_V1_STR}/documents/", headers=normal_user_token_headers
    )

    ids = {d["id"] for d in r.json()["data"]}
    assert mine["id"] in ids
    assert theirs["id"] not in ids


def test_delete_document_removes_its_chunks(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    doc = _upload(client, normal_user_token_headers, make_pdf_bytes(["bye"])).json()
    stored = db.exec(
        select(DocumentChunk).where(DocumentChunk.document_id == doc["id"])
    ).all()
    assert len(stored) == 1

    r = client.delete(
        f"{settings.API_V1_STR}/documents/{doc['id']}",
        headers=normal_user_token_headers,
    )

    assert r.status_code == 200
    db.expire_all()
    remaining = db.exec(
        select(DocumentChunk).where(DocumentChunk.document_id == doc["id"])
    ).all()
    assert remaining == []


def test_read_other_users_document_returns_403(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    doc = _upload(client, superuser_token_headers, make_pdf_bytes(["admin"])).json()

    r = client.get(
        f"{settings.API_V1_STR}/documents/{doc['id']}",
        headers=normal_user_token_headers,
    )

    assert r.status_code == 403
