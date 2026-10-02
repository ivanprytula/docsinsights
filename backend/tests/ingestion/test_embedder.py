import math

import pytest

from app.ingestion.embedder import (
    EMBEDDING_DIMENSIONS,
    FastEmbedEmbedder,
)


@pytest.fixture(scope="module")
def embedder() -> FastEmbedEmbedder:
    return FastEmbedEmbedder()


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return dot / (math.hypot(*a) * math.hypot(*b))


def test_embedding_dimensions_come_from_the_model_registry():
    assert EMBEDDING_DIMENSIONS == 384


def test_embed_documents_returns_one_vector_per_text(embedder: FastEmbedEmbedder):
    vectors = embedder.embed_documents(["first page", "second page"])
    assert len(vectors) == 2
    assert all(len(v) == EMBEDDING_DIMENSIONS for v in vectors)


def test_embed_documents_with_empty_list_returns_empty_list(
    embedder: FastEmbedEmbedder,
):
    assert embedder.embed_documents([]) == []


def test_embed_query_returns_vector_of_model_dimensions(embedder: FastEmbedEmbedder):
    assert (
        len(embedder.embed_query("what is the refund policy?")) == EMBEDDING_DIMENSIONS
    )


def test_related_text_scores_higher_than_unrelated_text(embedder: FastEmbedEmbedder):
    query = embedder.embed_query("how do I get my money back?")
    refund, weather = embedder.embed_documents(
        ["Refunds are issued within 14 days of purchase.", "It will rain on Tuesday."]
    )
    assert _cosine(query, refund) > _cosine(query, weather)
