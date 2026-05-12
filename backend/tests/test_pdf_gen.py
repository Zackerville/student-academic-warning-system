import sys
import pytest
from fpdf import FPDF
from fpdf.enums import XPos, YPos

sys.path.append("/app")
from app.ai.chatbot.rag import parse_document_bytes, chunk_pages


def _make_test_pdf() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(
        200,
        10,
        text="Hello World, this is a test PDF",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
        align="C",
    )
    return bytes(pdf.output())


def test_pdf_parse_and_chunk():
    pdf_bytes = _make_test_pdf()
    pages = parse_document_bytes("test.pdf", pdf_bytes)
    assert len(pages) >= 1, "Should parse at least 1 page"
    chunks = chunk_pages(pages)
    assert len(chunks) >= 1, "Should produce at least 1 chunk"
    assert chunks[0].content, "First chunk should have content"
