from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass

from sqlalchemy import cast, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Text

from app.ai.chatbot.providers import HashEmbeddingProvider, get_embedding_provider
from app.ai.chatbot.rag import chunk_pages, parse_document_bytes
from app.core.config import settings
from app.models.document import Document


@dataclass
class SearchHit:
    document: Document
    distance: float

    @property
    def score(self) -> float:
        return max(0.0, 1.0 - self.distance)


async def ingest_document(
    db: AsyncSession,
    *,
    filename: str,
    data: bytes,
    uploaded_by=None,
    replace_existing: bool = True,
) -> list[Document]:
    pages = await asyncio.to_thread(parse_document_bytes, filename, data)
    chunks = await asyncio.to_thread(chunk_pages, pages)
    if not chunks:
        raise ValueError(
            "Không trích xuất được văn bản từ file. Nếu đây là PDF scan, hãy thử file rõ nét hơn; "
            "nếu là PDF có thể copy chữ, có thể file dùng font/encoding đặc biệt chưa OCR được."
        )

    if replace_existing:
        await db.execute(delete(Document).where(Document.source_file == filename))

    provider = get_embedding_provider()
    documents: list[Document] = []
    for chunk in chunks:
        embedding, provider_name = await _embed_with_fallback(
            provider,
            chunk.content,
            task_type="retrieval_document",
        )
        document = Document(
            filename=filename,
            source_file=filename,
            content=chunk.content,
            embedding=embedding,
            chunk_index=chunk.chunk_index,
            page_number=chunk.page_number,
            metadata_json={"embedding_provider": provider_name},
            uploaded_by=uploaded_by,
            is_active=True,
        )
        db.add(document)
        documents.append(document)

    await db.commit()
    result = await db.execute(
        select(Document)
        .where(Document.source_file == filename)
        .order_by(Document.chunk_index.asc())
    )
    return list(result.scalars().all())


async def search_documents(
    db: AsyncSession,
    question: str,
    *,
    top_k: int | None = None,
) -> list[SearchHit]:
    provider = get_embedding_provider()
    embedding, _provider_name = await _embed_with_fallback(
        provider,
        question,
        task_type="retrieval_query",
    )
    limit = top_k or settings.RAG_TOP_K
    distance_expr = Document.embedding.cosine_distance(embedding)
    result = await db.execute(
        select(Document, distance_expr.label("distance"))
        .where(Document.is_active.is_(True), Document.embedding.is_not(None))
        .order_by(distance_expr)
        .limit(limit)
    )
    vector_hits = [
        SearchHit(document=document, distance=float(distance or 0.0))
        for document, distance in result.all()
    ]
    keyword_hits = await _search_documents_by_keywords(db, question, limit=limit)
    return _merge_hits(keyword_hits + vector_hits, limit)


async def _embed_with_fallback(provider, text: str, *, task_type: str) -> tuple[list[float], str]:
    try:
        return await provider.embed(text, task_type=task_type), provider.name
    except Exception:
        if provider.name == "hash":
            raise
        fallback = HashEmbeddingProvider()
        return await fallback.embed(text, task_type=task_type), fallback.name


async def _search_documents_by_keywords(
    db: AsyncSession,
    question: str,
    *,
    limit: int,
) -> list[SearchHit]:
    terms = _keyword_terms(question)
    if not terms:
        return []

    result = await db.execute(
        select(Document)
        .where(
            Document.is_active.is_(True),
            or_(*(Document.content.ilike(f"%{term}%") for term in terms)),
        )
        .limit(40)
    )
    scored = []
    for document in result.scalars().all():
        score = _keyword_score(document.content, terms)
        if score > 0:
            scored.append((score, document))

    scored.sort(key=lambda item: item[0], reverse=True)
    hits = []
    for score, document in scored[:limit]:
        distance = max(0.0, 1.0 - min(0.98, score / 12.0))
        hits.append(SearchHit(document=document, distance=distance))
    return hits


def _keyword_terms(question: str) -> list[str]:
    q = question.lower()
    base_terms = [
        "điểm trung bình tích lũy",
        "trung bình tích lũy",
        "xếp loại học lực",
        "hạng tốt nghiệp",
        "xếp loại tốt nghiệp",
        "tốt nghiệp",
        "xuất sắc",
        "giỏi",
        "khá",
        "gpa",
    ]
    terms = [term for term in base_terms if term in q]
    for token in q.replace("/", " ").replace(".", " ").replace(",", " ").split():
        token = token.strip()
        if len(token) >= 4 and token not in {"theo", "mới", "nhất", "phòng", "đào", "tạo", "không", "nhiêu"}:
            terms.append(token)

    unique_terms: list[str] = []
    for term in terms:
        if term and term not in unique_terms:
            unique_terms.append(term)
    return unique_terms[:10]


def _keyword_score(content: str, terms: list[str]) -> float:
    text = content.lower()
    score = 0.0
    for term in terms:
        if term in text:
            score += 2.0 if " " in term else 1.0
    if "giỏi" in text and ("tốt nghiệp" in text or "xếp loại" in text):
        score += 4.0
    if "từ 3,2" in text or "3,2 đến cận 3,6" in text:
        score += 4.0
    if "từ 3,6" in text or "3,6 đến 4,0" in text:
        score += 2.0
    return score


def _merge_hits(hits: list[SearchHit], limit: int) -> list[SearchHit]:
    merged: OrderedDict[str, SearchHit] = OrderedDict()
    for hit in hits:
        key = str(hit.document.id)
        existing = merged.get(key)
        if existing is None or hit.score > existing.score:
            merged[key] = hit
    return list(merged.values())[:limit]


async def list_document_groups(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(
            Document.source_file,
            func.min(Document.filename).label("filename"),
            func.count(Document.id).label("chunks_count"),
            func.bool_or(Document.is_active).label("is_active"),
            func.max(Document.uploaded_at).label("uploaded_at"),
            func.max(cast(Document.uploaded_by, Text)).label("uploaded_by"),
            func.count(func.distinct(Document.page_number)).label("pages_count"),
        )
        .group_by(Document.source_file)
        .order_by(func.max(Document.uploaded_at).desc())
    )
    groups = []
    for row in result.all():
        groups.append(
            {
                "source_file": row.source_file,
                "filename": row.filename,
                "chunks_count": row.chunks_count,
                "is_active": bool(row.is_active),
                "uploaded_at": row.uploaded_at,
                "uploaded_by": row.uploaded_by,
                "pages_count": row.pages_count or 0,
            }
        )
    return groups


async def set_document_group_active(db: AsyncSession, source_file: str, is_active: bool) -> int:
    result = await db.execute(
        update(Document)
        .where(Document.source_file == source_file)
        .values(is_active=is_active)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return int(result.rowcount or 0)


async def delete_document_group(db: AsyncSession, source_file: str) -> int:
    result = await db.execute(delete(Document).where(Document.source_file == source_file))
    await db.commit()
    return int(result.rowcount or 0)


def dedupe_hits_by_source(hits: list[SearchHit]) -> list[SearchHit]:
    seen: OrderedDict[str, SearchHit] = OrderedDict()
    for hit in hits:
        key = f"{hit.document.source_file}:{hit.document.chunk_index}"
        seen.setdefault(key, hit)
    return list(seen.values())
