"""Pydantic schemas cho Study Plan + Recommender (M6)."""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CreditLoadRecommendation(BaseModel):
    """Đề xuất số tín chỉ HK tới."""
    min_credits: int
    recommended_credits: int
    max_credits: int
    rationale: str
    based_on_gpa: float
    warning_level: int


class RetakeCourseItem(BaseModel):
    """1 môn nên học lại / cải thiện."""
    course_id: UUID
    course_code: str
    course_name: str
    credits: int
    last_grade_letter: Optional[str]
    last_total_score: Optional[float]
    last_semester: str
    reason: str  # "F chưa qua" / "Điểm thấp ảnh hưởng GPA" / "Đã học lại nhưng vẫn F"
    priority: int  # 1 = cao nhất


class SuggestedCourseItem(BaseModel):
    """Môn gợi ý đăng ký HK tới (khác với retake)."""
    course_id: UUID
    course_code: str
    course_name: str
    credits: int
    rationale: str


class StudyPlanResponse(BaseModel):
    """Response toàn bộ kế hoạch học tập cho SV."""
    credit_load: CreditLoadRecommendation
    retake_courses: list[RetakeCourseItem]
    suggested_courses: list[SuggestedCourseItem]
    total_unresolved_failed: int
    total_credits_earned: int
    gpa_cumulative: float
