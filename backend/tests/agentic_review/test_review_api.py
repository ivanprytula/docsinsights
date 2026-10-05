from collections.abc import Generator, Sequence

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlmodel import Session

from app.agentic_review.models import ReviewVerdict, Verdict
from app.api.deps import require_reviewer
from app.core.config import settings
from app.ingestion.embedder import get_embedder
from app.main import app
from app.retrieval.models import SearchHit
from tests.utils.embedder import KeywordEmbedder
from tests.utils.pdf import make_pdf_bytes
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email

UPLOAD_URL = f"{settings.API_V1_STR}/documents/upload"


def _review_url(document_id: str) -> str:
    return f"{settings.API_V1_STR}/documents/{document_id}/review"


class FakeReviewer:
    def __init__(
        self,
        *,
        verdict: ReviewVerdict | None = None,
        error: Exception | None = None,
    ) -> None:
        self.calls: list[tuple[str, list[SearchHit]]] = []
        self._verdict = verdict
        self._error = error

    def review(
        self, *, requirement: str, passages: Sequence[SearchHit]
    ) -> ReviewVerdict | None:
        self.calls.append((requirement, list(passages)))
        if self._error is not None:
            raise self._error
        return self._verdict


@pytest.fixture(autouse=True)
def keyword_embedder() -> Generator[None]:
    app.dependency_overrides[get_embedder] = KeywordEmbedder
    yield
    app.dependency_overrides.pop(get_embedder)


def _use_reviewer(reviewer: FakeReviewer) -> None:
    app.dependency_overrides[require_reviewer] = lambda: reviewer


@pytest.fixture(autouse=True)
def _clear_reviewer_override() -> Generator[None]:
    yield
    app.dependency_overrides.pop(require_reviewer, None)


@pytest.fixture(scope="module")
def review_user_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(client=client, email=random_email(), db=db)


def _upload(client: TestClient, headers: dict[str, str], pages: list[str]) -> dict:
    r = client.post(
        UPLOAD_URL,
        headers=headers,
        files={"file": ("policy.pdf", make_pdf_bytes(pages), "application/pdf")},
    )
    assert r.status_code == 201
    return r.json()


def test_review_returns_one_page_cited_finding_per_requirement(
    client: TestClient, review_user_headers: dict[str, str]
) -> None:
    verdict = ReviewVerdict(
        verdict=Verdict.SATISFIED, rationale="Refunds in 14 days.", citations=[1]
    )
    fake = FakeReviewer(verdict=verdict)
    _use_reviewer(fake)
    doc = _upload(
        client, review_user_headers, ["Sunny weather", "refund within 14 days"]
    )

    r = client.post(
        _review_url(doc["id"]),
        headers=review_user_headers,
        json={"requirements": ["refund", "weather"], "limit": 1},
    )

    assert r.status_code == 200
    findings = r.json()["findings"]
    assert [f["requirement"] for f in findings] == ["refund", "weather"]
    assert findings[0]["verdict"] == "satisfied"
    assert findings[0]["sources"][0]["page_num"] == 2
    assert len(fake.calls) == 2


def test_review_of_another_users_document_returns_404_without_calling_the_model(
    client: TestClient,
    review_user_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    fake = FakeReviewer()
    _use_reviewer(fake)
    theirs = _upload(client, superuser_token_headers, ["refund secret"])

    r = client.post(
        _review_url(theirs["id"]),
        headers=review_user_headers,
        json={"requirements": ["refund"]},
    )

    assert r.status_code == 404
    assert r.json()["detail"] == "Document not found"
    assert fake.calls == []


def test_review_has_a_null_verdict_when_the_model_declines(
    client: TestClient, review_user_headers: dict[str, str]
) -> None:
    _use_reviewer(FakeReviewer(verdict=None))
    doc = _upload(client, review_user_headers, ["refund here"])

    r = client.post(
        _review_url(doc["id"]),
        headers=review_user_headers,
        json={"requirements": ["refund"]},
    )

    assert r.status_code == 200
    assert r.json()["findings"][0]["verdict"] is None


def test_review_returns_502_with_a_generic_message_when_the_model_call_fails(
    client: TestClient, review_user_headers: dict[str, str]
) -> None:
    failure = anthropic.APIConnectionError(
        request=httpx2.Request("POST", "https://api.anthropic.com/secret-path")
    )
    _use_reviewer(FakeReviewer(error=failure))
    doc = _upload(client, review_user_headers, ["refund here"])

    r = client.post(
        _review_url(doc["id"]),
        headers=review_user_headers,
        json={"requirements": ["refund"]},
    )

    assert r.status_code == 502
    assert r.json()["detail"] == "Review service unavailable"


def test_review_returns_503_when_no_api_key_is_configured(
    client: TestClient,
    review_user_headers: dict[str, str],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)

    r = client.post(
        _review_url("00000000-0000-0000-0000-000000000000"),
        headers=review_user_headers,
        json={"requirements": ["refund"]},
    )

    assert r.status_code == 503


@pytest.mark.parametrize(
    "body",
    [{"requirements": []}, {"requirements": [""]}, {"requirements": ["x"] * 21}],
)
def test_review_rejects_invalid_requests_with_422(
    client: TestClient, review_user_headers: dict[str, str], body: dict
) -> None:
    _use_reviewer(FakeReviewer())

    r = client.post(
        _review_url("00000000-0000-0000-0000-000000000000"),
        headers=review_user_headers,
        json=body,
    )

    assert r.status_code == 422
