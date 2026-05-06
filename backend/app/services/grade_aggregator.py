"""
Grade aggregation helpers — single source of truth cho quy chế HCMUT.

Các hàm trong module này dùng chung bởi:
- `app.api.v1.students` (dashboard, GPA endpoints)
- `app.ai.prediction.features` (feature engineering cho XGBoost)
- `app.ai.prediction.model` (sync stats trước khi predict)
- `app.ai.chatbot.personal` (build student context cho chatbot)

KHÔNG đặt ở `app.api.v1.students` để tránh circular import:
AI / chatbot modules KHÔNG được phép phụ thuộc vào API layer.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.student import Student
from app.services.gpa_calculator import (
    _SPECIAL_LETTERS,
    grade_letter_to_gpa_point,
    score_to_gpa_point,
)


def enrollment_gpa_point(e: Enrollment) -> float | None:
    """
    GPA point thang 4 của một enrollment, None nếu RT/MT/DT/đặc biệt hoặc chưa có điểm.

    Ưu tiên grade_letter trước total_score (vì khi import từ myBK, letter là nguồn chính thức).
    """
    letter = e.grade_letter
    if letter and letter in _SPECIAL_LETTERS:
        return None  # RT/MT/DT/CT/VT/CH/KD/VP/HT — không tính GPA
    if letter:
        return grade_letter_to_gpa_point(letter)
    if e.total_score is not None:
        return score_to_gpa_point(e.total_score)
    return None


def is_credit_bearing(e: Enrollment) -> bool:
    """True nếu môn có tín chỉ học vụ > 0 (loại trừ SHSV, PE, AV nhu cầu...)."""
    return bool(e.course and e.course.credits > 0)


def count_unresolved_failed(effective_enrollments: list[Enrollment]) -> int:
    """
    Đếm môn chưa đạt còn HIỆU LỰC sau khi áp quy chế "highest wins".

    Input phải là kết quả của `effective_enrollments_per_course`.
    Bỏ môn 0 TC vì rớt môn 0 TC không tính vào học vụ.
    """
    return sum(
        1 for e in effective_enrollments
        if e.status == EnrollmentStatus.failed and is_credit_bearing(e)
    )


def has_gpa_bearing_grade(enrollments: list[Enrollment]) -> bool:
    """
    True nếu SV đã có ít nhất một môn có tín chỉ và có điểm GPA hợp lệ.

    Dùng để tránh coi tài khoản mới tinh (GPA mặc định 0.0 vì chưa import điểm)
    là sinh viên rơi vào diện buộc thôi học.
    """
    return any(
        is_credit_bearing(e) and enrollment_gpa_point(e) is not None
        for e in enrollments
    )


def effective_enrollments_per_course(enrollments: list[Enrollment]) -> list[Enrollment]:
    """
    Quy chế HCMUT — học lại / học cải thiện:

    Với mỗi `course_id`, lấy enrollment có GPA point CAO NHẤT (không phải mới nhất).
    - B (3.0) HK241 + học cải thiện C (2.0) HK251 → giữ B (HK241)
    - F (0)  HK241 + học lại đạt B (3.0) HK251   → giữ B (HK251)
    - Trùng điểm tuyệt đối → tiebreak bằng học kỳ muộn hơn (semester string sort lexicographic)

    Nếu không lần nào có gpa_point hợp lệ (toàn RT/MT/DT) → fallback lấy lần MỚI NHẤT
    để vẫn xử lý đúng credits/status.

    Bỏ qua enrollment status='enrolled' chưa có điểm — không override điểm cũ
    bằng môn đang học chưa có kết quả.
    """
    by_course: dict[UUID, list[Enrollment]] = {}
    for e in enrollments:
        is_in_progress = (
            e.status == EnrollmentStatus.enrolled
            and not e.grade_letter
            and e.total_score is None
        )
        if is_in_progress:
            continue
        by_course.setdefault(e.course_id, []).append(e)

    effective: list[Enrollment] = []
    for attempts in by_course.values():
        scored = [(e, enrollment_gpa_point(e)) for e in attempts]
        scored = [(e, p) for e, p in scored if p is not None]

        if scored:
            best = max(scored, key=lambda x: (x[1], x[0].semester))[0]
            effective.append(best)
        else:
            effective.append(max(attempts, key=lambda e: e.semester))
    return effective


async def sync_student_stats(student: Student, db: AsyncSession) -> None:
    """
    Recompute `gpa_cumulative` + `credits_earned` từ enrollments, lưu vào DB.

    Áp đầy đủ quy chế HCMUT highest-wins — gọi sau mỗi lần SV cập nhật điểm
    hoặc trước khi predict để stats không bị stale.
    """
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student.id)
        .options(selectinload(Enrollment.course))
    )
    all_enrollments = result.scalars().all()

    effective = effective_enrollments_per_course(all_enrollments)

    # Credits earned: môn passed/exempt có TC > 0 (mỗi môn chỉ tính 1 lần)
    passed_statuses = {EnrollmentStatus.passed, EnrollmentStatus.exempt}
    credits_earned = sum(
        e.course.credits for e in effective
        if e.status in passed_statuses and e.course.credits > 0
    )

    # GPA tích lũy: chỉ dùng điểm hiệu lực, bỏ môn 0 TC + RT/MT/DT
    total_pts = 0.0
    total_tc = 0
    for e in effective:
        if e.course.credits == 0:
            continue
        letter = e.grade_letter
        if letter and letter in _SPECIAL_LETTERS:
            continue
        gpa_pt = None
        if letter:
            gpa_pt = grade_letter_to_gpa_point(letter)
        elif e.total_score is not None:
            gpa_pt = score_to_gpa_point(e.total_score)
        if gpa_pt is None:
            continue
        total_pts += gpa_pt * e.course.credits
        total_tc += e.course.credits

    gpa_cumulative = round(total_pts / total_tc, 2) if total_tc > 0 else 0.0

    student.gpa_cumulative = gpa_cumulative
    student.credits_earned = credits_earned
    await db.commit()
