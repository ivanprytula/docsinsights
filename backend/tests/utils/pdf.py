import io


def make_pdf_bytes(pages_text: list[str]) -> bytes:
    """Build a minimal single-page-per-string PDF, no dependency beyond stdlib.

    Avoids pulling in a PDF-generation library just to produce test fixtures.
    """
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(len(pages_text)))
    objects.append(
        f"<< /Type /Pages /Kids [{kids}] /Count {len(pages_text)} >>".encode()
    )

    font_obj_num = 3 + 2 * len(pages_text)
    for i, text in enumerate(pages_text):
        content_obj_num = 3 + 2 * i + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 {font_obj_num} 0 R >> >> "
            f"/MediaBox [0 0 200 200] /Contents {content_obj_num} 0 R >>".encode()
        )
        stream = f"BT /F1 12 Tf 10 100 Td ({text}) Tj ET".encode()
        objects.append(
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(buf.tell())
        buf.write(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_offset = buf.tell()
    n = len(objects) + 1
    buf.write(f"xref\n0 {n}\n".encode())
    buf.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        buf.write(f"{off:010d} 00000 n \n".encode())
    buf.write(
        f"trailer\n<< /Size {n} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    )
    return buf.getvalue()
