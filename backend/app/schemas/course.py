from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CourseBase(BaseModel):
    course_code: str
    name: str
    credits: int
    faculty: str


class CourseCreate(CourseBase):
    pass


class CourseResponse(CourseBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
