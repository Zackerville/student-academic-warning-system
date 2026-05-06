from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

from app.models.enrollment import EnrollmentStatus
from app.schemas.course import CourseResponse


class EnrollmentCreate(BaseModel):
    course_id: UUID
    semester: str
    midterm_weight: float = 0.3
    lab_weight: float = 0.0
    other_weight: float = 0.0
    final_weight: float = 0.7

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "EnrollmentCreate":
        total = round(self.midterm_weight + self.lab_weight + self.other_weight + self.final_weight, 4)
        if total != 1.0:
            raise ValueError(f"Tổng trọng số phải bằng 1.0 (hiện tại: {total})")
        return self


class GradeUpdate(BaseModel):
    midterm_score: Optional[float] = None
    lab_score: Optional[float] = None
    other_score: Optional[float] = None
    final_score: Optional[float] = None
    attendance_rate: Optional[float] = None
    midterm_weight: Optional[float] = None
    lab_weight: Optional[float] = None
    other_weight: Optional[float] = None
    final_weight: Optional[float] = None

    @field_validator("midterm_score", "lab_score", "other_score", "final_score")
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
    lab_score: Optional[float]
    other_score: Optional[float]
    final_score: Optional[float]
    midterm_weight: float
    lab_weight: float
    other_weight: float
    final_weight: float
    total_score: Optional[float]
    grade_letter: Optional[str]
    status: EnrollmentStatus
    attendance_rate: Optional[float]
    is_finalized: bool
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EnrollmentWithCourse(EnrollmentResponse):
    course: CourseResponse


class GpaHistoryEntry(BaseModel):
    semester: str
    semester_gpa: float
    credits_taken: int
    courses_count: int


class GradeUpdateOutcome(BaseModel):
    """
    Response của PUT /me/enrollments/{id}/grades — gồm enrollment + warning info.
    FE dùng warning_created/warning_level/ai_early_warning để toast thông báo.
    """
    enrollment: EnrollmentResponse
    warning_created: bool = False
    warning_level: Optional[int] = None
    warning_reason: Optional[str] = None
    ai_early_warning: bool = False
