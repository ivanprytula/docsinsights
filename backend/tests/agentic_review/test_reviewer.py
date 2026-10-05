import uuid
from types import SimpleNamespace
from typing import Any, cast

import anthropic

from app.agentic_review.models import ReviewVerdict, Verdict
from app.agentic_review.reviewer import REVIEW_MODEL, SYSTEM_PROMPT, ClaudeReviewer
from app.retrieval.models import SearchHit


def _hit(text: str) -> SearchHit:
    return SearchHit(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename="policy.pdf",
        page_num=3,
        text=text,
        score=0.5,
    )


class StubMessages:
    def __init__(self, *, stop_reason: str, parsed: ReviewVerdict | None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._response = SimpleNamespace(stop_reason=stop_reason, parsed_output=parsed)

    def parse(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return self._response


def _reviewer(stub: StubMessages) -> ClaudeReviewer:
    return ClaudeReviewer(cast(anthropic.Anthropic, SimpleNamespace(messages=stub)))


def test_review_returns_parsed_verdict_and_requests_the_schema() -> None:
    verdict = ReviewVerdict(
        verdict=Verdict.SATISFIED, rationale="Breach notice in 72h.", citations=[1]
    )
    stub = StubMessages(stop_reason="end_turn", parsed=verdict)

    result = _reviewer(stub).review(
        requirement="Breaches are notified within 72 hours",
        passages=[_hit("Notify within 72 hours")],
    )

    assert result == verdict
    call = stub.calls[0]
    assert call["model"] == REVIEW_MODEL
    assert call["system"] == SYSTEM_PROMPT
    assert call["output_format"] is ReviewVerdict
    assert "Notify within 72 hours" in call["messages"][0]["content"]


def test_review_returns_none_when_the_model_refuses() -> None:
    stub = StubMessages(stop_reason="refusal", parsed=None)

    assert _reviewer(stub).review(requirement="R", passages=[_hit("t")]) is None


def test_review_returns_none_when_output_was_truncated() -> None:
    stub = StubMessages(stop_reason="max_tokens", parsed=None)

    assert _reviewer(stub).review(requirement="R", passages=[_hit("t")]) is None
