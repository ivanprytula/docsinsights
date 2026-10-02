from collections.abc import Sequence

from app.ingestion.embedder import EMBEDDING_DIMENSIONS

KEYWORDS = ("refund", "weather", "invoice")


class KeywordEmbedder:
    """Deterministic embedder: one axis per keyword, last axis for everything else."""

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        matched = False
        for axis, keyword in enumerate(KEYWORDS):
            if keyword in text.lower():
                vector[axis] = 1.0
                matched = True
        if not matched:
            vector[len(KEYWORDS)] = 1.0
        return vector

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
