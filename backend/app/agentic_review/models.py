from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.retrieval.models import AnswerSource


class Verdict(StrEnum):
    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"
    NOT_FOUND = "not_found"


class ReviewVerdict(BaseModel):
    """The model's structured judgment on one review question; `citations` are passage numbers."""

    verdict: Verdict
    rationale: str
    citations: list[int]


class Finding(BaseModel):
    """One requirement's outcome; `verdict` is None when the model gave no valid verdict."""

    requirement: str
    verdict: Verdict | None
    rationale: str | None
    sources: list[AnswerSource]


class ReviewRequest(BaseModel):
    requirements: list[
        Annotated[str, StringConstraints(min_length=1, max_length=500)]
    ] = Field(min_length=1, max_length=20)
    limit: int = Field(default=5, ge=1, le=20)


class Review(BaseModel):
    findings: list[Finding]
