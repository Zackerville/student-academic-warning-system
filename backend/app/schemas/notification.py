from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.notification import NotificationType


class NotificationResponse(BaseModel):
    id: UUID
    student_id: UUID
    type: NotificationType
    title: str
    content: str
    is_read: bool
    sent_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationCreate(BaseModel):
    student_id: UUID
    type: NotificationType
    title: str
    content: str
