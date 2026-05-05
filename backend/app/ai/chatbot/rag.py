from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from app.core.config import settings


@dataclass
class ParsedPage:
    page_number: int | None
    text: str


@dataclass
class DocumentChunk:
    content: str
    chunk_index: int
    page_number: int | None


def parse_document_bytes(filename: str, data: bytes) -> list[ParsedPage]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(data)
    if suffix == ".docx":
        return _parse_docx(data)
    if suffix in {".txt", ".md"}:
        return [ParsedPage(page_number=None, text=_decode_text(data))]
    raise ValueError("Chỉ hỗ trợ PDF, DOCX, TXT hoặc MD")


def chunk_pages(pages: list[ParsedPage]) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    chunk_index = 0
    chunk_size = max(settings.RAG_CHUNK_SIZE, 200)
    overlap = min(max(settings.RAG_CHUNK_OVERLAP, 0), chunk_size // 2)

    for page in pages:
        text = normalize_text(page.text)
        if not text:
            continue
        words = text.split()
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            content = " ".join(words[start:end]).strip()
            if content:
                chunks.append(
                    DocumentChunk(
                        content=content,
                        chunk_index=chunk_index,
                        page_number=page.page_number,
                    )
                )
                chunk_index += 1
            if end == len(words):
                break
            start = max(end - overlap, start + 1)

    return chunks


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def citation_snippet(text: str, query: str | None = None, limit: int = 520) -> str:
    normalized = normalize_text(text).replace("\n", " ")
    if len(normalized) <= limit:
        return normalized
    if query:
        start = _snippet_start(normalized, query, limit)
        if start > 0:
            snippet = normalized[start:start + limit].strip()
            return "..." + snippet.rsplit(" ", 1)[0] + "..."
    return normalized[: limit - 3].rsplit(" ", 1)[0] + "..."


def _snippet_start(text: str, query: str, limit: int) -> int:
    lowered = text.lower()
    terms = _snippet_terms(query)
    center = -1
    for term in terms:
        position = lowered.find(term)
        if position >= 0:
            center = position
            break
    if center < 0:
        return 0
    return max(0, center - limit // 3)


def _snippet_terms(query: str) -> list[str]:
    q = query.lower()
    priority = [
        "từ 3,2",
        "3,2 đến cận 3,6",
        "từ 3,6",
        "3,6 đến 4,0",
        "giỏi",
        "xuất sắc",
        "khá",
        "điểm trung bình tích lũy",
        "trung bình tích lũy",
        "xếp loại học lực",
        "xếp loại tốt nghiệp",
        "hạng tốt nghiệp",
        "tốt nghiệp",
        "gpa",
    ]
    terms = [term for term in priority if term in q]
    terms.extend(token for token in re.findall(r"[\wÀ-ỹ]+", q) if len(token) >= 4)
    unique_terms: list[str] = []
    for term in terms:
        if term not in unique_terms:
            unique_terms.append(term)
    return unique_terms


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "cp1258", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _parse_pdf(data: bytes) -> list[ParsedPage]:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError("Thiếu thư viện pymupdf. Hãy cài dependencies backend.") from exc

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError("File PDF bị lỗi định dạng hoặc có mật khẩu bảo vệ.") from exc

    pages: list[ParsedPage] = []
    try:
        for index, page in enumerate(doc, start=1):
            text = _extract_pdf_text_layer(page)
            pages.append(ParsedPage(page_number=index, text=text))

        if settings.RAG_ENABLE_OCR and not _has_enough_text(pages):
            pages = _ocr_pdf(doc)
    finally:
        doc.close()

    return pages


def _extract_pdf_text_layer(page) -> str:
    text_parts: list[str] = []

    for mode in ("text", "blocks"):
        try:
            extracted = page.get_text(mode, sort=True)
        except TypeError:
            extracted = page.get_text(mode)
        except Exception:
            continue

        if mode == "blocks" and isinstance(extracted, list):
            extracted = "\n".join(
                str(block[4])
                for block in extracted
                if len(block) > 4 and str(block[4]).strip()
            )
        if isinstance(extracted, str) and extracted.strip():
            text_parts.append(extracted)

    return normalize_text("\n".join(text_parts))


def _has_enough_text(pages: list[ParsedPage]) -> bool:
    text = " ".join(page.text for page in pages)
    letters = re.findall(r"[A-Za-zÀ-ỹ0-9]", text)
    return len(letters) >= 80


def _ocr_pdf(doc) -> list[ParsedPage]:
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "PDF không có text layer đọc được và backend thiếu pytesseract/Pillow để OCR."
        ) from exc

    pages: list[ParsedPage] = []
    max_pages = max(settings.RAG_OCR_MAX_PAGES, 1)
    zoom = max(settings.RAG_OCR_DPI, 120) / 72

    import fitz  # type: ignore

    for index, page in enumerate(doc, start=1):
        if index > max_pages:
            break
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        image = Image.open(BytesIO(pixmap.tobytes("png")))
        text = pytesseract.image_to_string(image, lang=settings.RAG_OCR_LANG)
        pages.append(ParsedPage(page_number=index, text=normalize_text(text)))

    return pages


def _parse_docx(data: bytes) -> list[ParsedPage]:
    try:
        from docx import Document as DocxDocument  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Thiếu thư viện python-docx. Hãy cài dependencies backend.") from exc

    from io import BytesIO

    document = DocxDocument(BytesIO(data))
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    return [ParsedPage(page_number=None, text="\n".join(paragraphs))]
