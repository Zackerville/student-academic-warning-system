"""
Study Plan Service (M6.2) — orchestrator cho Recommender.

Trách nhiệm:
- Load enrollments + apply HCMUT highest-wins
- Phân loại unresolved_failed vs low_grade_passed
- Gọi recommender pure functions
- Build StudyPlanResponse đầy đủ cho FE
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.student import Student
from app.schemas.study_plan import (
    CreditLoadRecommendation,
    RetakeCourseItem,
    StudyPlanResponse,
    SuggestedCourseItem,
)
from app.services import recommender
from app.services.grade_aggregator import (
    count_unresolved_failed,
    effective_enrollments_per_course,
    is_credit_bearing,
)


_LOW_GRADE_LETTERS = {"D", "D+"}


async def build_study_plan(db: AsyncSession, student: Student) -> StudyPlanResponse:
    enrollments_result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student.id)
        .options(selectinload(Enrollment.course))
    )
    all_enrollments = list(enrollments_result.scalars().all())
    effective = effective_enrollments_per_course(all_enrollments)

    unresolved_failed_dicts = []
    low_grade_passed_dicts = []
    for e in effective:
        if not e.course or not is_credit_bearing(e):
            continue
        course_data = {
            "course_id": e.course.id,
            "course_code": e.course.course_code,
            "course_name": e.course.name,
            "credits": e.course.credits,
            "last_grade_letter": e.grade_letter,
            "last_total_score": e.total_score,
            "last_semester": e.semester,
        }
        if e.status == EnrollmentStatus.failed:
            unresolved_failed_dicts.append(course_data)
        elif e.status == EnrollmentStatus.passed and e.grade_letter in _LOW_GRADE_LETTERS:
            if (student.gpa_cumulative or 0.0) < 2.0:
                low_grade_passed_dicts.append(course_data)

    credit_load = recommender.recommend_credit_load(
        gpa_cumulative=student.gpa_cumulative or 0.0,
        warning_level=student.warning_level or 0,
    )
    retakes = recommender.recommend_retake_priority(
        unresolved_failed=unresolved_failed_dicts,
        low_grade_passed=low_grade_passed_dicts,
    )

    retake_items = [
        RetakeCourseItem(
            course_id=r.course_id,
            course_code=r.course_code,
            course_name=r.course_name,
            credits=r.credits,
            last_grade_letter=r.last_grade_letter,
            last_total_score=r.last_total_score,
            last_semester=r.last_semester,
            reason=r.reason,
            priority=r.priority,
        )
        for r in retakes
    ]

    suggested = await _suggest_new_courses(
        db, student, exclude_course_ids={e.course_id for e in effective}
    )

    return StudyPlanResponse(
        credit_load=CreditLoadRecommendation(
            min_credits=credit_load.min_credits,
            recommended_credits=credit_load.recommended_credits,
            max_credits=credit_load.max_credits,
            rationale=credit_load.rationale,
            based_on_gpa=student.gpa_cumulative or 0.0,
            warning_level=student.warning_level or 0,
        ),
        retake_courses=retake_items,
        suggested_courses=suggested,
        total_unresolved_failed=count_unresolved_failed(effective),
        total_credits_earned=student.credits_earned or 0,
        gpa_cumulative=student.gpa_cumulative or 0.0,
    )


async def _suggest_new_courses(
    db: AsyncSession, student: Student, *, exclude_course_ids: set
) -> list[SuggestedCourseItem]:
    """
    Heuristic gợi ý môn mới: ưu tiên môn cùng khoa SV, chưa đăng ký, credits 2-4.
    Đây là rule-based đơn giản — Phase 2 mới làm CF/CB recommender.
    """
    from app.models.course import Course

    if not student.faculty:
        return []

    result = await db.execute(
        select(Course)
        .where(
            Course.faculty == student.faculty,
            Course.credits.between(2, 4),
        )
        .order_by(Course.course_code.asc())
        .limit(10)
    )
    candidates = [c for c in result.scalars().all() if c.id not in exclude_course_ids]
    return [
        SuggestedCourseItem(
            course_id=c.id,
            course_code=c.course_code,
            course_name=c.name,
            credits=c.credits,
            rationale=f"Môn {c.credits} TC thuộc {student.faculty} — phù hợp tiến độ chương trình.",
        )
        for c in candidates[:5]
    ]
