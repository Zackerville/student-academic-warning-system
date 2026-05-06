"""
Study Plan API (M6.3) — /api/v1/study-plan

Endpoints:
- GET /study-plan/me                — credit load + retake + suggested
- GET /study-plan/me/credit-load    — chỉ phần credit load (lighter response)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_student, get_db
from app.models.student import Student
from app.schemas.study_plan import CreditLoadRecommendation, StudyPlanResponse
from app.services import recommender, study_plan as study_plan_service

router = APIRouter(prefix="/study-plan", tags=["study-plan"])


@router.get("/me", response_model=StudyPlanResponse)
async def get_my_study_plan(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    return await study_plan_service.build_study_plan(db, student)


@router.get("/me/credit-load", response_model=CreditLoadRecommendation)
async def get_my_credit_load(
    student: Student = Depends(get_current_student),
):
    """Endpoint nhẹ — chỉ gợi ý số tín chỉ, không load enrollments."""
    cl = recommender.recommend_credit_load(
        gpa_cumulative=student.gpa_cumulative or 0.0,
        warning_level=student.warning_level or 0,
    )
    return CreditLoadRecommendation(
        min_credits=cl.min_credits,
        recommended_credits=cl.recommended_credits,
        max_credits=cl.max_credits,
        rationale=cl.rationale,
        based_on_gpa=student.gpa_cumulative or 0.0,
        warning_level=student.warning_level or 0,
    )
