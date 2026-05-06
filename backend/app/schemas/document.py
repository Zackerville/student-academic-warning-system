from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    source_file: str
    chunk_index: int
    page_number: Optional[int] = None
    is_active: bool
    uploaded_at: datetime
    uploaded_by: Optional[UUID]

    model_config = {"from_attributes": True}


class DocumentToggle(BaseModel):
    is_active: bool


class DocumentGroupResponse(BaseModel):
    source_file: str
    filename: str
    chunks_count: int
    is_active: bool
    uploaded_at: datetime
    uploaded_by: Optional[UUID] = None
    pages_count: int = 0


class DocumentBatchUploadItem(BaseModel):
    filename: str
    status: str
    chunks_count: int = 0
    error: Optional[str] = None


class DocumentBatchUploadResponse(BaseModel):
    uploaded: int
    failed: int
    total_chunks: int
    results: list[DocumentBatchUploadItem]
