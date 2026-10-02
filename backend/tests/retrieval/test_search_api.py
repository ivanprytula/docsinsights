from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.ingestion.embedder import get_embedder
from app.main import app
from tests.utils.embedder import KeywordEmbedder
from tests.utils.pdf import make_pdf_bytes

UPLOAD_URL = f"{settings.API_V1_STR}/documents/upload"
SEARCH_URL = f"{settings.API_V1_STR}/search"


@pytest.fixture(autouse=True)
def keyword_embedder() -> Generator[None]:
    app.dependency_overrides[get_embedder] = KeywordEmbedder
    yield
    app.dependency_overrides.pop(get_embedder)


def _upload(
    client: TestClient, headers: dict[str, str], pages: list[str], name: str
) -> dict:
    r = client.post(
        UPLOAD_URL,
        headers=headers,
        files={"file": (name, make_pdf_bytes(pages), "application/pdf")},
    )
    assert r.status_code == 201
    return r.json()


def _search(client: TestClient, headers: dict[str, str], query: str, **extra):
    return client.post(SEARCH_URL, headers=headers, json={"query": query, **extra})


def test_search_returns_closest_passage_first_with_page_and_filename(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    doc = _upload(
        client,
        normal_user_token_headers,
        ["Sunny weather all week", "Our refund policy is 14 days"],
        "policies.pdf",
    )

    r = _search(client, normal_user_token_headers, "refund")

    assert r.status_code == 200
    top = r.json()["data"][0]
    assert top["document_id"] == doc["id"]
    assert top["filename"] == "policies.pdf"
    assert top["page_num"] == 2
    assert top["text"] == "Our refund policy is 14 days"
    assert top["score"] == pytest.approx(1.0)


def test_search_orders_hits_by_descending_score(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    _upload(client, normal_user_token_headers, ["refund", "weather"], "a.pdf")

    r = _search(client, normal_user_token_headers, "refund")

    scores = [hit["score"] for hit in r.json()["data"]]
    assert scores == sorted(scores, reverse=True)


def test_search_never_returns_another_users_passages(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    theirs = _upload(
        client, superuser_token_headers, ["refund secrets"], "admin-only.pdf"
    )
    mine = _upload(client, normal_user_token_headers, ["refund mine"], "mine.pdf")

    r = _search(client, normal_user_token_headers, "refund", limit=20)

    ids = {hit["document_id"] for hit in r.json()["data"]}
    assert mine["id"] in ids
    assert theirs["id"] not in ids


def test_search_respects_limit(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    _upload(client, normal_user_token_headers, ["refund one", "refund two"], "l.pdf")

    r = _search(client, normal_user_token_headers, "refund", limit=1)

    body = r.json()
    assert body["count"] == 1
    assert len(body["data"]) == 1


def test_search_with_document_id_only_returns_that_document(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    first = _upload(client, normal_user_token_headers, ["refund one"], "first.pdf")
    second = _upload(client, normal_user_token_headers, ["refund two"], "second.pdf")

    r = _search(
        client, normal_user_token_headers, "refund", limit=20, document_id=first["id"]
    )

    ids = {hit["document_id"] for hit in r.json()["data"]}
    assert ids == {first["id"]}
    assert second["id"] not in ids


def test_search_with_another_users_document_id_returns_404(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    theirs = _upload(client, superuser_token_headers, ["refund secret"], "admin.pdf")

    r = _search(client, normal_user_token_headers, "refund", document_id=theirs["id"])

    assert r.status_code == 404
    assert r.json()["detail"] == "Document not found"


def test_search_with_unknown_document_id_returns_404(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = _search(
        client,
        normal_user_token_headers,
        "refund",
        document_id="00000000-0000-7000-8000-000000000000",
    )

    assert r.status_code == 404
    assert r.json()["detail"] == "Document not found"


def test_search_with_malformed_document_id_returns_422(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = _search(client, normal_user_token_headers, "refund", document_id="nope")

    assert r.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"query": ""},
        {"query": "x" * 1001},
        {"query": "ok", "limit": 0},
        {"query": "ok", "limit": 21},
    ],
)
def test_search_rejects_invalid_requests_with_422(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    payload: dict,
) -> None:
    r = client.post(SEARCH_URL, headers=normal_user_token_headers, json=payload)

    assert r.status_code == 422


def test_search_requires_authentication(client: TestClient) -> None:
    r = client.post(SEARCH_URL, json={"query": "refund"})

    assert r.status_code == 401
