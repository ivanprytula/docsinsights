import re
import uuid
from typing import BinaryIO

from pydantic import BaseModel, ConfigDict
from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PyPdfError

# bge-small truncates input at 512 tokens. English averages ~1.3 tokens per word,
# but emails, URLs and code run higher, so 250 words leaves headroom.
MAX_CHUNK_WORDS = 250
CHUNK_OVERLAP_WORDS = 50


class Chunk(BaseModel):
    """A window of one page's text, ready for embedding."""

    model_config = ConfigDict(frozen=True)

    doc_id: uuid.UUID
    page_num: int
    text: str


class UnsupportedDocumentError(Exception):
    """Raised when a file cannot be parsed as a PDF."""


class EncryptedDocumentError(UnsupportedDocumentError):
    """Raised when a PDF is password-protected."""


def split_into_windows(
    text: str,
    *,
    max_words: int = MAX_CHUNK_WORDS,
    overlap_words: int = CHUNK_OVERLAP_WORDS,
) -> list[str]:
    """Split text into overlapping word windows, preserving original whitespace."""
    words = list(re.finditer(r"\S+", text))
    if len(words) <= max_words:
        return [text]
    step = max_words - overlap_words
    windows = []
    for start in range(0, len(words), step):
        end = min(start + max_words, len(words))  # min()
        windows.append(text[words[start].start() : words[end - 1].end()])
        if end == len(words):
            break
    return windows


def parse_pdf(file: BinaryIO, *, doc_id: uuid.UUID) -> list[Chunk]:
    """Extract overlapping text Chunks from each page of a PDF file.

    Pages longer than `MAX_CHUNK_WORDS` yield several chunks sharing a `page_num`.
    Empty pages (no extractable text) are skipped. Raises
    `EncryptedDocumentError` for password-protected files and
    `UnsupportedDocumentError` for anything else pypdf cannot read.
    """
    try:
        reader = PdfReader(file)
        chunks = []
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text().strip()
            if text:
                chunks.extend(
                    Chunk(doc_id=doc_id, page_num=page_num, text=window)
                    for window in split_into_windows(text)
                )
    except FileNotDecryptedError as e:
        raise EncryptedDocumentError("PDF is password-protected") from e
    except PyPdfError as e:
        raise UnsupportedDocumentError(f"Could not read PDF: {e}") from e
    return chunks
