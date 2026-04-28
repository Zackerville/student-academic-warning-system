from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel

from app.models.event import EventType, TargetAudience


class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    event_type: EventType
    target_audience: TargetAudience = TargetAudience.all
    target_value: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    is_mandatory: bool = False


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    target_audience: Optional[TargetAudience] = None
    target_value: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_mandatory: Optional[bool] = None


class EventResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    event_type: EventType
    target_audience: TargetAudience
    target_value: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    is_mandatory: bool
    created_by: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}
