import io
import uuid

import pytest
from pypdf import PdfWriter

from app.ingestion.document_parser import (
    EncryptedDocumentError,
    UnsupportedDocumentError,
    parse_pdf,
    split_into_windows,
)
from tests.utils.pdf import make_pdf_bytes


def test_parse_pdf_extracts_one_chunk_per_short_page() -> None:
    doc_id = uuid.uuid4()
    pdf_bytes = make_pdf_bytes(["Hello World", "Second Page"])

    chunks = parse_pdf(io.BytesIO(pdf_bytes), doc_id=doc_id)

    assert len(chunks) == 2
    assert chunks[0].doc_id == doc_id
    assert chunks[0].page_num == 1
    assert chunks[0].text == "Hello World"
    assert chunks[1].page_num == 2
    assert chunks[1].text == "Second Page"


def test_parse_pdf_skips_pages_with_no_extractable_text() -> None:
    doc_id = uuid.uuid4()
    pdf_bytes = make_pdf_bytes(["", "Only real page"])

    chunks = parse_pdf(io.BytesIO(pdf_bytes), doc_id=doc_id)

    assert len(chunks) == 1
    assert chunks[0].page_num == 2
    assert chunks[0].text == "Only real page"


def test_parse_pdf_raises_on_non_pdf_input() -> None:
    doc_id = uuid.uuid4()
    not_a_pdf = io.BytesIO(b"this is not a pdf file")

    with pytest.raises(UnsupportedDocumentError):
        parse_pdf(not_a_pdf, doc_id=doc_id)


def test_parse_pdf_raises_on_truncated_pdf() -> None:
    pdf_bytes = make_pdf_bytes(["Hello World", "Second Page"])
    truncated = io.BytesIO(pdf_bytes[: len(pdf_bytes) // 2])

    with pytest.raises(UnsupportedDocumentError):
        parse_pdf(truncated, doc_id=uuid.uuid4())


def test_parse_pdf_raises_on_empty_input() -> None:
    with pytest.raises(UnsupportedDocumentError):
        parse_pdf(io.BytesIO(b""), doc_id=uuid.uuid4())


def test_parse_pdf_raises_encrypted_error_on_password_protected_pdf() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("secret")
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)

    with pytest.raises(EncryptedDocumentError):
        parse_pdf(buf, doc_id=uuid.uuid4())


def test_split_into_windows_keeps_short_text_as_one_window() -> None:
    assert split_into_windows("one two three", max_words=5, overlap_words=1) == [
        "one two three"
    ]


def test_split_into_windows_overlaps_consecutive_windows() -> None:
    text = " ".join(f"w{i}" for i in range(10))

    windows = split_into_windows(text, max_words=4, overlap_words=1)

    assert windows == ["w0 w1 w2 w3", "w3 w4 w5 w6", "w6 w7 w8 w9"]


def test_split_into_windows_covers_every_word_when_length_is_not_a_multiple() -> None:
    text = " ".join(f"w{i}" for i in range(11))

    windows = split_into_windows(text, max_words=4, overlap_words=1)

    assert windows[-1].endswith("w10")
    assert set(" ".join(windows).split()) == set(text.split())


def test_split_into_windows_does_not_emit_a_window_fully_inside_the_previous() -> None:
    text = " ".join(f"w{i}" for i in range(7))

    windows = split_into_windows(text, max_words=4, overlap_words=1)

    assert windows == ["w0 w1 w2 w3", "w3 w4 w5 w6"]


def test_split_into_windows_collapses_newlines_and_repeated_spaces() -> None:
    text = "alpha\nbeta  gamma\n\ndelta epsilon"

    assert split_into_windows(text, max_words=10, overlap_words=1) == [
        "alpha beta gamma delta epsilon"
    ]
    assert split_into_windows(text, max_words=3, overlap_words=1)[0] == (
        "alpha beta gamma"
    )


def test_parse_pdf_collapses_whitespace_in_extracted_text() -> None:
    pdf_bytes = make_pdf_bytes(["one   two    three"])

    chunks = parse_pdf(io.BytesIO(pdf_bytes), doc_id=uuid.uuid4())

    assert chunks[0].text == "one two three"


def test_parse_pdf_splits_long_page_into_chunks_sharing_the_page_number() -> None:
    long_page = " ".join(f"w{i}" for i in range(600))
    pdf_bytes = make_pdf_bytes([long_page, "Short"])

    chunks = parse_pdf(io.BytesIO(pdf_bytes), doc_id=uuid.uuid4())

    page_one = [c for c in chunks if c.page_num == 1]
    assert len(page_one) == 3
    assert [c.page_num for c in chunks][-1] == 2
    assert chunks[-1].text == "Short"
    assert page_one[-1].text.endswith("w599")
