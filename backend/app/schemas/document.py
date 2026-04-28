from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    source_file: str
    chunk_index: int
    is_active: bool
    uploaded_at: datetime
    uploaded_by: Optional[UUID]

    model_config = {"from_attributes": True}


class DocumentToggle(BaseModel):
    is_active: bool
