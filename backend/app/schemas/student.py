from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.user import UserResponse


class StudentBase(BaseModel):
    mssv: str
    full_name: str
    faculty: str
    major: str
    cohort: int


class StudentResponse(StudentBase):
    id: UUID
    user_id: UUID
    gpa_cumulative: float
    credits_earned: int
    warning_level: int
    created_at: datetime

    model_config = {"from_attributes": True}


class StudentWithUser(StudentResponse):
    user: UserResponse
