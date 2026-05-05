from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.ai.chatbot.chains import (
    ask_chatbot,
    clear_chat_history,
    default_suggestions,
    get_chat_history,
    stream_chatbot_response,
)
from app.core.deps import get_current_student, get_db
from app.models.student import Student
from app.schemas.chatbot import (
    ChatCitation,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    SuggestionResponse,
)

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


@router.post("/ask", response_model=ChatResponse)
async def ask(
    payload: ChatRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    return await ask_chatbot(db, student=student, question=payload.question)


@router.post("/ask/stream")
async def ask_stream(
    payload: ChatRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    return StreamingResponse(
        stream_chatbot_response(db, student=student, question=payload.question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/history", response_model=list[ChatMessageResponse])
async def history(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    messages = await get_chat_history(db, student)
    return [
        ChatMessageResponse(
            id=message.id,
            role=message.role,
            content=message.content,
            citations=[
                ChatCitation.model_validate(citation)
                for citation in (message.citations or [])
            ],
            created_at=message.created_at,
        )
        for message in messages
    ]


@router.delete("/history", response_model=dict)
async def clear_history(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    deleted = await clear_chat_history(db, student)
    return {"deleted": deleted}


@router.get("/suggestions", response_model=SuggestionResponse)
async def suggestions(student: Student = Depends(get_current_student)):
    return SuggestionResponse(suggestions=default_suggestions(student))
