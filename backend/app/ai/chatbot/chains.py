from __future__ import annotations

import json

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chatbot.personal import build_student_context
from app.ai.chatbot.providers import ProviderConfigError, get_chat_provider
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
    hits = (
        dedupe_hits_by_source(await search_documents(db, question))
        if _should_search_documents(question)
        else []
    )
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
        )
        for index, hit in enumerate(hits, start=1)
    ]
    retrieved_context = _format_retrieved_context(citations)
    provider = get_chat_provider()

    try:
        answer = await provider.answer(question, retrieved_context, student_context, history)
    except ProviderConfigError as exc:
        fallback = get_chat_provider() if provider.name == "extractive" else None
        if fallback is None:
            from app.ai.chatbot.providers import ExtractiveChatProvider

            fallback = ExtractiveChatProvider()
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
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def clear_chat_history(db: AsyncSession, student: Student) -> int:
    result = await db.execute(delete(ChatMessage).where(ChatMessage.student_id == student.id))
    await db.commit()
    return int(result.rowcount or 0)


def default_suggestions(student: Student) -> list[str]:
    suggestions = [
        "Em đang ở mức cảnh báo nào và nên ưu tiên gì?",
        "Nếu rớt một môn bắt buộc thì có ảnh hưởng GPA như thế nào?",
        "Em nên học lại hay cải thiện điểm môn nào trước?",
        "Điều kiện bị cảnh báo học vụ theo tài liệu hiện có là gì?",
    ]
    if student.warning_level > 0:
        suggestions.insert(0, "Với mức cảnh báo hiện tại, em nên làm gì trong học kỳ tới?")
    return suggestions[:5]


async def stream_chat_response(response: ChatResponse):
    for token in _chunk_text(response.answer):
        yield f"data: {json.dumps({'type': 'delta', 'content': token}, ensure_ascii=False)}\n\n"
    yield (
        "data: "
        + json.dumps(
            {
                "type": "done",
                "citations": [citation.model_dump(mode="json") for citation in response.citations],
                "provider": response.provider,
            },
            ensure_ascii=False,
        )
        + "\n\n"
    )


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


def _should_search_documents(question: str) -> bool:
    q = question.lower()
    regulation_keywords = [
        "quy chế",
        "quy định",
        "nội quy",
        "điều kiện",
        "điều khoản",
        "bao nhiêu thì",
        "mức 1",
        "mức 2",
        "mức 3",
        "buộc thôi học",
        "cảnh báo học vụ",
        "học phí",
        "hoàn trả",
        "tốt nghiệp",
        "đăng ký môn",
        "hủy môn",
        "rút môn",
        "bảo lưu",
        "miễn",
        "tương đương",
        "thay thế",
        "theo trường",
        "theo hcmut",
    ]
    return any(keyword in q for keyword in regulation_keywords)


def _chunk_text(text: str, size: int = 24):
    words = text.split(" ")
    for index in range(0, len(words), size):
        chunk = " ".join(words[index:index + size])
        if index + size < len(words):
            chunk += " "
        yield chunk
