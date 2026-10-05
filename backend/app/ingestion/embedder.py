from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

from fastembed import TextEmbedding

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_DIMENSIONS = 384
# fastembed defaults to 256, which let the container grow past 4 GB while embedding one PDF.
EMBED_BATCH_SIZE = 32


def _lookup_dimensions(model_name: str) -> int:
    """Read dimensions from fastembed's registry (no model load); fall back if unlisted."""
    try:
        return TextEmbedding.get_embedding_size(model_name)
    except ValueError:
        return DEFAULT_DIMENSIONS


EMBEDDING_DIMENSIONS = _lookup_dimensions(EMBEDDING_MODEL)


class Embedder(Protocol):
    """Turns text into vectors of `EMBEDDING_DIMENSIONS`; swappable per ADR-0002."""

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedEmbedder:
    """CPU embedder backed by fastembed; the model loads on first use."""

    def __init__(self) -> None:
        self._model: TextEmbedding | None = None

    def _get_model(self) -> TextEmbedding:
        if self._model is None:
            self._model = TextEmbedding(EMBEDDING_MODEL)
        return self._model

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed passages for storage; no prefix."""
        return [
            v.tolist()
            for v in self._get_model().embed(list(texts), batch_size=EMBED_BATCH_SIZE)
        ]

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query; bge-small v1.5 needs no instruction prefix (ADR-0005)."""
        return self.embed_documents([text])[0]


@lru_cache
def get_embedder() -> Embedder:
    """One embedder per process so the model loads once."""
    return FastEmbedEmbedder()
