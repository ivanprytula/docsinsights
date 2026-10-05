from collections.abc import Generator, Sequence

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlmodel import Session

from app.api.deps import require_answerer
from app.core.config import settings
from app.ingestion.embedder import get_embedder
from app.main import app
from app.retrieval.models import SearchHit
from tests.utils.embedder import KeywordEmbedder
from tests.utils.pdf import make_pdf_bytes
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email

UPLOAD_URL = f"{settings.API_V1_STR}/documents/upload"
ANSWER_URL = f"{settings.API_V1_STR}/answer"


class FakeAnswerer:
    """Records what it was given; returns a canned answer or raises."""

    def __init__(
        self, *, reply: str | None = "14 days [1].", error: Exception | None = None
    ) -> None:
        self.calls: list[tuple[str, list[SearchHit]]] = []
        self._reply = reply
        self._error = error

    def answer(self, *, question: str, passages: Sequence[SearchHit]) -> str | None:
        self.calls.append((question, list(passages)))
        if self._error is not None:
            raise self._error
        return self._reply


@pytest.fixture(autouse=True)
def keyword_embedder() -> Generator[None]:
    app.dependency_overrides[get_embedder] = KeywordEmbedder
    yield
    app.dependency_overrides.pop(get_embedder)


def _use_answerer(answerer: FakeAnswerer) -> None:
    app.dependency_overrides[require_answerer] = lambda: answerer


@pytest.fixture(autouse=True)
def _clear_answerer_override() -> Generator[None]:
    yield
    app.dependency_overrides.pop(require_answerer, None)


@pytest.fixture(scope="module")
def answer_user_headers(client: TestClient, db: Session) -> dict[str, str]:
    """A user of its own, so these uploads never leak into other modules' searches."""
    return authentication_token_from_email(client=client, email=random_email(), db=db)


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


def _answer(client: TestClient, headers: dict[str, str], question: str, **extra):
    return client.post(
        ANSWER_URL, headers=headers, json={"question": question, **extra}
    )


def test_answer_returns_the_answer_with_numbered_sources(
    client: TestClient, answer_user_headers: dict[str, str]
) -> None:
    fake = FakeAnswerer()
    _use_answerer(fake)
    doc = _upload(
        client,
        answer_user_headers,
        ["Sunny weather all week", "Our refund policy is 14 days"],
        "policies.pdf",
    )

    r = _answer(client, answer_user_headers, "refund", document_id=doc["id"], limit=1)

    assert r.status_code == 200
    assert r.json() == {
        "answer": "14 days [1].",
        "sources": [
            {
                "n": 1,
                "filename": "policies.pdf",
                "page_num": 2,
                "text": "Our refund policy is 14 days",
            }
        ],
    }


def test_answer_gives_the_answerer_the_question_and_passages_best_first(
    client: TestClient, answer_user_headers: dict[str, str]
) -> None:
    fake = FakeAnswerer()
    _use_answerer(fake)
    doc = _upload(client, answer_user_headers, ["weather only", "refund here"], "o.pdf")

    _answer(client, answer_user_headers, "refund", document_id=doc["id"])

    question, passages = fake.calls[0]
    assert question == "refund"
    assert [p.page_num for p in passages] == [2, 1]


def test_answer_with_another_users_document_returns_404_without_calling_the_model(
    client: TestClient,
    answer_user_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    fake = FakeAnswerer()
    _use_answerer(fake)
    theirs = _upload(client, superuser_token_headers, ["refund secret"], "admin.pdf")

    r = _answer(client, answer_user_headers, "refund", document_id=theirs["id"])

    assert r.status_code == 404
    assert r.json()["detail"] == "Document not found"
    assert fake.calls == []


def test_answer_without_any_documents_skips_the_model(
    client: TestClient, db: Session
) -> None:
    fake = FakeAnswerer()
    _use_answerer(fake)
    headers = authentication_token_from_email(
        client=client, email=random_email(), db=db
    )

    r = _answer(client, headers, "refund")

    assert r.status_code == 200
    assert r.json() == {"answer": None, "sources": []}
    assert fake.calls == []


def test_answer_is_null_but_keeps_sources_when_the_model_declines(
    client: TestClient, answer_user_headers: dict[str, str]
) -> None:
    _use_answerer(FakeAnswerer(reply=None))
    doc = _upload(client, answer_user_headers, ["refund here"], "d.pdf")

    r = _answer(client, answer_user_headers, "refund", document_id=doc["id"])

    body = r.json()
    assert body["answer"] is None
    assert len(body["sources"]) == 1


def test_answer_returns_502_with_a_generic_message_when_the_model_call_fails(
    client: TestClient, answer_user_headers: dict[str, str]
) -> None:
    failure = anthropic.APIConnectionError(
        request=httpx2.Request("POST", "https://api.anthropic.com/secret-path")
    )
    _use_answerer(FakeAnswerer(error=failure))
    doc = _upload(client, answer_user_headers, ["refund here"], "e.pdf")

    r = _answer(client, answer_user_headers, "refund", document_id=doc["id"])

    assert r.status_code == 502
    assert r.json()["detail"] == "Answer service unavailable"


def test_answer_returns_503_when_no_api_key_is_configured(
    client: TestClient,
    answer_user_headers: dict[str, str],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)

    r = _answer(client, answer_user_headers, "refund")

    assert r.status_code == 503
    assert r.json()["detail"] == "Answers are not available"


def test_answer_rejects_invalid_requests_with_422(
    client: TestClient, answer_user_headers: dict[str, str]
) -> None:
    _use_answerer(FakeAnswerer())

    assert _answer(client, answer_user_headers, "").status_code == 422
    assert _answer(client, answer_user_headers, "q", limit=0).status_code == 422


def test_answer_requires_authentication(client: TestClient) -> None:
    r = client.post(ANSWER_URL, json={"question": "refund"})

    assert r.status_code == 401
