import sys
from fpdf import FPDF

sys.path.append("/app")
from app.ai.chatbot.rag import parse_document_bytes, chunk_pages

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.cell(200, 10, txt="Hello World, this is a test PDF", ln=True, align="C")
pdf_bytes = pdf.output(dest="S").encode("latin1")

pages = parse_document_bytes("test.pdf", pdf_bytes)
chunks = chunk_pages(pages)
print("Chunks count:", len(chunks))
if chunks:
    print("First chunk:", chunks[0].content[:100])
