from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)


class ChatCitation(BaseModel):
    index: int
    document_id: UUID
    source_file: str
    filename: str
    chunk_index: int
    page_number: Optional[int] = None
    snippet: str
    score: float
    # vector = cosine similarity từ pgvector embedding
    # keyword = ilike match từ keyword whitelist (score normalize khác — KHÔNG so sánh cross-mode)
    # merged = trùng cả 2, lấy điểm cao hơn
    match_type: Literal["vector", "keyword", "merged"] = "vector"


class ChatResponse(BaseModel):
    answer: str
    citations: list[ChatCitation] = []
    provider: str
    used_personal_context: bool = False


class ChatMessageResponse(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    citations: list[ChatCitation] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class SuggestionResponse(BaseModel):
    suggestions: list[str]
