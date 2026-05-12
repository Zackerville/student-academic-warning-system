from __future__ import annotations

import json
from typing import AsyncIterator

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chatbot.personal import build_student_context
from app.ai.chatbot.providers import (
    ExtractiveChatProvider,
    ProviderConfigError,
    get_chat_provider,
)
from app.ai.chatbot.rag import citation_snippet
from app.ai.chatbot.vectorstore import dedupe_hits_by_source, search_documents
from app.models.chat_message import ChatMessage
from app.models.student import Student
from app.schemas.chatbot import ChatCitation, ChatResponse


async def ask_chatbot(
    db: AsyncSession,
    *,
    student: Student,
    question: str,
    save_history: bool = True,
) -> ChatResponse:
    history = await _recent_history(db, student)
    student_context = await build_student_context(student, db)
    hits = dedupe_hits_by_source(await search_documents(db, question))
    citations = [
        ChatCitation(
            index=index,
            document_id=hit.document.id,
            source_file=hit.document.source_file,
            filename=hit.document.filename,
            chunk_index=hit.document.chunk_index,
            page_number=hit.document.page_number,
            snippet=citation_snippet(hit.document.content, question),
            score=round(hit.score, 4),
            match_type=hit.match_type,
        )
        for index, hit in enumerate(hits, start=1)
    ]
    retrieved_context = _format_retrieved_context(citations)
    provider = get_chat_provider()

    try:
        answer = await provider.answer(question, retrieved_context, student_context, history)
    except ProviderConfigError as exc:
        fallback = ExtractiveChatProvider() if provider.name != "extractive" else provider
        answer = (
            f"Cấu hình model hiện tại chưa dùng được ({exc}). "
            "Mình tạm trả lời bằng chế độ trích xuất nội bộ.\n\n"
            + await fallback.answer(question, retrieved_context, student_context, history)
        )
        provider = fallback

    response = ChatResponse(
        answer=answer,
        citations=citations,
        provider=provider.name,
        used_personal_context=bool(student_context),
    )

    if save_history:
        db.add(ChatMessage(student_id=student.id, role="user", content=question))
        db.add(
            ChatMessage(
                student_id=student.id,
                role="assistant",
                content=answer,
                citations=[citation.model_dump(mode="json") for citation in citations],
            )
        )
        await db.commit()

    return response


async def get_chat_history(db: AsyncSession, student: Student, limit: int = 50) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.student_id == student.id)
        # Secondary sort by role ASC: "assistant" (a) before "user" (u) within same timestamp.
        # After reversed(), user always precedes assistant — stable even when both share
        # the same created_at (server_default=now() = transaction start).
        .order_by(ChatMessage.created_at.desc(), ChatMessage.role.asc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def clear_chat_history(db: AsyncSession, student: Student) -> int:
    result = await db.execute(delete(ChatMessage).where(ChatMessage.student_id == student.id))
    await db.commit()
    return int(result.rowcount or 0)


def default_suggestions(student: Student) -> list[str]:
    """
    Smart context-aware suggestions — chọn câu hỏi phù hợp nhất với tình trạng học vụ của SV.
    Priority: warning_level cao → câu hỏi khẩn cấp hơn; GPA thấp/tốt → câu hỏi tương ứng.
    """
    gpa = float(student.gpa_cumulative or 0.0)
    level = int(student.warning_level or 0)
    credits = int(student.credits_earned or 0)

    pool: list[tuple[int, str]] = []  # (priority, question) — lower = higher priority

    # === Theo warning level ===
    if level >= 3:
        pool += [
            (0, "Em đang bị buộc thôi học, còn cơ hội nào để tiếp tục không?"),
            (0, "Quy trình khiếu nại hoặc xin xem xét lại quyết định buộc thôi học là gì?"),
        ]
    elif level == 2:
        pool += [
            (0, "Với cảnh báo mức 2, em cần GPA tối thiểu bao nhiêu để thoát cảnh báo?"),
            (0, "Em nên đăng ký bao nhiêu tín chỉ trong học kỳ tới để cải thiện GPA an toàn?"),
        ]
    elif level == 1:
        pool += [
            (0, "Với cảnh báo mức 1, em cần làm gì trong học kỳ tới để không bị cảnh báo mức 2?"),
            (1, "Em nên ưu tiên học lại môn nào trước để cải thiện GPA nhanh nhất?"),
        ]
    else:
        pool += [
            (3, "Làm sao duy trì GPA ổn định và tránh bị cảnh báo học vụ?"),
        ]

    # === Theo GPA tích lũy ===
    if gpa < 1.2:
        pool += [
            (0, f"GPA em đang là {gpa:.1f}, ngưỡng tối thiểu để không bị buộc thôi học là bao nhiêu?"),
        ]
    elif gpa < 2.0:
        pool += [
            (1, f"GPA tích lũy {gpa:.1f} thì cần đạt GPA học kỳ bao nhiêu để kéo lên 2.0?"),
            (2, "Em nên học lại hay cải thiện điểm môn nào để tăng GPA hiệu quả nhất?"),
        ]
    elif gpa < 2.5:
        pool += [
            (2, "Chiến lược nào giúp nâng GPA từ vùng 2.0-2.5 lên trên 2.5?"),
        ]
    elif gpa >= 3.2:
        pool += [
            (3, "Em cần điều kiện gì để được xét học bổng hoặc khen thưởng?"),
            (3, "Quy định về học vượt hoặc rút ngắn thời gian đào tạo là gì?"),
        ]

    # === Theo số tín chỉ ===
    if credits < 30:
        pool += [
            (2, "Trong những học kỳ đầu, em nên đăng ký bao nhiêu tín chỉ là phù hợp?"),
        ]
    elif credits >= 100:
        pool += [
            (3, "Em sắp tốt nghiệp, điều kiện xét tốt nghiệp theo quy chế là gì?"),
        ]

    # === Câu hỏi chung luôn có ===
    pool += [
        (4, "Điều kiện bị cảnh báo học vụ theo quy chế Bách Khoa là gì?"),
        (4, "Quy định học lại và học cải thiện điểm tại HCMUT như thế nào?"),
        (5, "Nếu rớt một môn bắt buộc thì ảnh hưởng thế nào đến tiến độ tốt nghiệp?"),
        (5, "Chatbot có thể tư vấn gì dựa trên tình trạng học vụ hiện tại của em?"),
    ]

    # Sort by priority, deduplicate, take top 5
    seen: set[str] = set()
    result: list[str] = []
    for _, q in sorted(pool, key=lambda x: x[0]):
        if q not in seen:
            seen.add(q)
            result.append(q)
        if len(result) == 5:
            break
    return result


async def stream_chatbot_response(
    db: AsyncSession,
    *,
    student: Student,
    question: str,
    save_history: bool = True,
) -> AsyncIterator[str]:
    """
    Streaming pipeline thật cho chatbot — yield từng token SSE khi LLM sinh ra
    (Gemini native), hoặc fake-chunk theo cụm từ với extractive/HF/local fallback.

    SSE event format giữ nguyên tương thích với FE cũ:
      data: {"type":"delta","content":"..."}
      ...
      data: {"type":"done","citations":[...],"provider":"..."}
    """
    history = await _recent_history(db, student)
    student_context = await build_student_context(student, db)
    hits = dedupe_hits_by_source(await search_documents(db, question))
    citations = [
        ChatCitation(
            index=index,
            document_id=hit.document.id,
            source_file=hit.document.source_file,
            filename=hit.document.filename,
            chunk_index=hit.document.chunk_index,
            page_number=hit.document.page_number,
            snippet=citation_snippet(hit.document.content, question),
            score=round(hit.score, 4),
            match_type=hit.match_type,
        )
        for index, hit in enumerate(hits, start=1)
    ]
    retrieved_context = _format_retrieved_context(citations)

    primary = get_chat_provider()
    answer_parts: list[str] = []
    final_provider_name = primary.name

    async def _emit(text: str) -> str:
        answer_parts.append(text)
        return f"data: {json.dumps({'type': 'delta', 'content': text}, ensure_ascii=False)}\n\n"

    fallback_used = False
    try:
        async for chunk in primary.answer_stream(
            question, retrieved_context, student_context, history
        ):
            if chunk:
                yield await _emit(chunk)
    except ProviderConfigError as exc:
        # Streaming fail → fallback extractive (luôn chạy được, không cần API key).
        fallback_used = True
        fallback = ExtractiveChatProvider() if primary.name != "extractive" else primary
        prefix = (
            f"Cấu hình model hiện tại chưa dùng được ({exc}). "
            "Mình tạm trả lời bằng chế độ trích xuất nội bộ.\n\n"
        )
        yield await _emit(prefix)
        async for chunk in fallback.answer_stream(
            question, retrieved_context, student_context, history
        ):
            if chunk:
                yield await _emit(chunk)
        final_provider_name = fallback.name

    if not answer_parts and not fallback_used:
        yield await _emit("Mình chưa tạo được câu trả lời.")

    full_answer = "".join(answer_parts)
    yield (
        "data: "
        + json.dumps(
            {
                "type": "done",
                "citations": [c.model_dump(mode="json") for c in citations],
                "provider": final_provider_name,
            },
            ensure_ascii=False,
        )
        + "\n\n"
    )

    if save_history and full_answer:
        db.add(ChatMessage(student_id=student.id, role="user", content=question))
        db.add(
            ChatMessage(
                student_id=student.id,
                role="assistant",
                content=full_answer,
                citations=[c.model_dump(mode="json") for c in citations],
            )
        )
        await db.commit()


async def _recent_history(db: AsyncSession, student: Student) -> list[dict[str, str]]:
    messages = await get_chat_history(db, student, limit=12)
    return [{"role": item.role, "content": item.content} for item in messages]


def _format_retrieved_context(citations: list[ChatCitation]) -> str:
    lines = []
    for citation in citations:
        page = f", trang {citation.page_number}" if citation.page_number else ""
        lines.append(
            f"[{citation.index}] {citation.filename}{page}, đoạn {citation.chunk_index}: {citation.snippet}"
        )
    return "\n\n".join(lines)



