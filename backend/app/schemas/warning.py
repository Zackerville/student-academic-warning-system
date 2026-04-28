from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel

from app.models.warning import WarningCreatedBy


class WarningResponse(BaseModel):
    id: UUID
    student_id: UUID
    level: int
    semester: str
    reason: str
    gpa_at_warning: float
    ai_risk_score: Optional[float]
    is_resolved: bool
    sent_at: Optional[datetime]
    created_by: WarningCreatedBy
    created_at: datetime

    model_config = {"from_attributes": True}


class WarningCreate(BaseModel):
    student_id: UUID
    level: int
    semester: str
    reason: str
    gpa_at_warning: float
    ai_risk_score: Optional[float] = None


class WarningResolve(BaseModel):
    is_resolved: bool = True
