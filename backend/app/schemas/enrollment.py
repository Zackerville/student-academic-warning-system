from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.enrollment import EnrollmentStatus
from app.schemas.course import CourseResponse


class EnrollmentCreate(BaseModel):
    course_id: UUID
    semester: str


class GradeUpdate(BaseModel):
    midterm_score: Optional[float] = None
    final_score: Optional[float] = None
    attendance_rate: Optional[float] = None

    @field_validator("midterm_score", "final_score")
    @classmethod
    def score_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0 <= v <= 10):
            raise ValueError("Điểm phải từ 0 đến 10")
        return v

    @field_validator("attendance_rate")
    @classmethod
    def attendance_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0 <= v <= 100):
            raise ValueError("Tỷ lệ điểm danh phải từ 0 đến 100")
        return v


class EnrollmentResponse(BaseModel):
    id: UUID
    student_id: UUID
    course_id: UUID
    semester: str
    midterm_score: Optional[float]
    final_score: Optional[float]
    total_score: Optional[float]
    grade_letter: Optional[str]
    status: EnrollmentStatus
    attendance_rate: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class EnrollmentWithCourse(EnrollmentResponse):
    course: CourseResponse
