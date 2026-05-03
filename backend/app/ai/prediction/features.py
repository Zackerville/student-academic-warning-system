"""
Feature engineering — biến enrollments raw thành 1 row features cho XGBoost.

Áp dụng quy chế HCMUT "highest GPA wins" cho học lại / cải thiện
(xem `_effective_enrollments_per_course` trong app.api.v1.students).

Output: dict[str, float] với các feature đã quy đổi về "risk signal" rõ nghĩa.
Hầu hết feature càng lớn thì rủi ro càng cao; riêng recovered_failed_courses
là tín hiệu bảo vệ vì môn F đã được học lại đạt.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.students import (
    _count_unresolved_failed,
    _effective_enrollments_per_course,
    _enrollment_gpa_point,
    _is_credit_bearing,
)
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.student import Student
from app.services.gpa_calculator import (
    EnrollmentGrade,
    _SPECIAL_LETTERS,
    calculate_gpa_trend,
    calculate_semester_gpa,
)

# ─── Constants ───────────────────────────────────────────────

GPA_SAFE_TARGET = 2.0
ATTENDANCE_SAFE_MIN = 75.0
FEATURE_VERSION = "m4_v4_2026_05_04_no_zero_credit_f"

# Order of features (load-bearing — XGBoost requires same order in train + predict)
FEATURE_NAMES = [
    "gpa_cumulative_deficit",          # ↑ GPA càng thiếu so với 2.0 càng rủi ro
    "gpa_recent_deficit",              # ↑ GPA HK gần nhất càng thấp càng rủi ro
    "gpa_trend_drop",                  # ↑ GPA đang giảm càng rủi ro
    "low_gpa_streak",                  # ↑ nhiều HK liên tiếp GPA < 2.0
    "unresolved_failed_courses",       # ↑ chỉ đếm môn mà điểm hiệu lực vẫn F
    "unresolved_failed_last_semester", # ↑ F ở HK gần nhất và hiện vẫn chưa qua
    "unresolved_failed_retake_count",  # ↑ học lại rồi vẫn chưa qua
    "withdrawn_count",                 # ↑ rút môn còn là tín hiệu rủi ro
    "pass_rate_deficit",               # ↑ tỉ lệ qua môn càng thấp càng rủi ro
    "attendance_risk",                 # ↑ chỉ > 0 nếu điểm danh < 75%
    "recovered_failed_courses",        # ↓ từng F nhưng đã học lại đạt
]

# XGBoost monotonic constraints theo cùng thứ tự FEATURE_NAMES.
#  1: feature tăng thì risk không được giảm
# -1: feature tăng thì risk không được tăng
MONOTONIC_CONSTRAINTS = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1]


# ─── Helpers ────────────────────────────────────────────────

def _safe(value: Optional[float], default: float = 0.0) -> float:
    """Convert None/NaN → default."""
    if value is None:
        return default
    if isinstance(value, float) and np.isnan(value):
        return default
    return float(value)


def _gpa_deficit(gpa: float, target: float = GPA_SAFE_TARGET) -> float:
    """Khoảng thiếu GPA so với mốc an toàn; GPA tốt trả 0."""
    return round(max(0.0, target - _safe(gpa)), 3)


def _attendance_risk(avg_attendance: Optional[float]) -> float:
    """
    Quy đổi điểm danh thành risk signal.
    Không có dữ liệu hoặc >= 75% đều là 0 để tránh câu kiểu "80% tăng rủi ro".
    """
    if avg_attendance is None:
        return 0.0
    return round(max(0.0, ATTENDANCE_SAFE_MIN - avg_attendance) / ATTENDANCE_SAFE_MIN, 4)


def _per_semester_gpas(enrollments: list[Enrollment]) -> dict[str, float]:
    """Per-semester GPA (KHÔNG dedup) — show GPA từng HK historical."""
    semester_map: dict[str, list[EnrollmentGrade]] = {}
    for e in enrollments:
        if e.course.credits == 0:
            continue
        if e.grade_letter or e.total_score is not None:
            eg = EnrollmentGrade(
                credits=e.course.credits,
                grade_letter=e.grade_letter,
                total_score=e.total_score,
            )
            semester_map.setdefault(e.semester, []).append(eg)
    return {s: calculate_semester_gpa(grades) for s, grades in semester_map.items()}


def _real_attempts_by_course(enrollments: list[Enrollment]) -> dict[UUID, list[Enrollment]]:
    """
    Group các lần học thật theo course.
    Bỏ qua môn 0 TC và điểm đặc biệt RT/MT/DT/CT/... vì chúng không phải attempt
    có GPA để đánh giá học lại.
    """
    by_course: dict[UUID, list[Enrollment]] = {}
    for e in enrollments:
        if e.course.credits == 0:
            continue
        if e.grade_letter and e.grade_letter.upper() in _SPECIAL_LETTERS:
            continue
        if e.grade_letter or e.total_score is not None:
            by_course.setdefault(e.course_id, []).append(e)
    return by_course


def _retake_outcomes(
    enrollments: list[Enrollment],
    effective: list[Enrollment],
) -> tuple[int, int]:
    """
    Returns: (unresolved_failed_retake_count, recovered_failed_courses)

    - unresolved_failed_retake_count: từng F, đã có nhiều attempt, nhưng điểm hiệu lực vẫn F.
    - recovered_failed_courses: từng F, sau đó học lại/cải thiện và điểm hiệu lực đã đạt.
    """
    attempts_by_course = _real_attempts_by_course(enrollments)
    effective_by_course = {e.course_id: e for e in effective}

    unresolved_failed_retake = 0
    recovered_failed = 0

    for course_id, attempts in attempts_by_course.items():
        if len(attempts) < 2:
            continue
        had_failed = any(e.status == EnrollmentStatus.failed for e in attempts)
        if not had_failed:
            continue

        winner = effective_by_course.get(course_id)
        if winner is None:
            continue
        if winner.status == EnrollmentStatus.failed:
            unresolved_failed_retake += 1
        elif winner.status in (EnrollmentStatus.passed, EnrollmentStatus.exempt):
            recovered_failed += 1

    return unresolved_failed_retake, recovered_failed


def _low_gpa_streak(per_semester: dict[str, float]) -> int:
    """Số HK liên tiếp gần nhất có GPA < 2.0."""
    semesters_sorted = sorted(per_semester.keys(), reverse=True)
    streak = 0
    for s in semesters_sorted:
        if per_semester[s] < 2.0:
            streak += 1
        else:
            break
    return streak


# ─── Main extract function ──────────────────────────────────

@dataclass
class FeatureResult:
    student_id: UUID
    features: dict[str, float]
    label: int  # warning_level >= 1


async def extract_features(
    student: Student,
    enrollments: list[Enrollment],
) -> dict[str, float]:
    """
    Extract features cho 1 SV. Inputs đã eager-loaded để tránh N+1.

    Args:
        student: Student record (đã sync stats)
        enrollments: List enrollments với eager-loaded course

    Returns dict matching FEATURE_NAMES.
    """
    effective = _effective_enrollments_per_course(enrollments)

    # Status counts từ effective (per course unique).
    # Nếu một môn từng F nhưng đã học lại đạt, môn đó KHÔNG còn nằm ở unresolved_failed.
    unresolved_failed = _count_unresolved_failed(effective)
    withdrawn_count = sum(
        1 for e in effective
        if e.status == EnrollmentStatus.withdrawn and _is_credit_bearing(e)
    )

    # Per-semester GPA (no dedup)
    per_sem_gpa = _per_semester_gpas(enrollments)
    semesters_sorted = sorted(per_sem_gpa.keys())
    semester_gpas_list = [per_sem_gpa[s] for s in semesters_sorted]
    last_sem = semesters_sorted[-1] if semesters_sorted else None

    # Failed last semester, nhưng chỉ giữ nếu môn đó hiện vẫn chưa qua.
    unresolved_failed_last_sem = 0
    if last_sem:
        effective_status_by_course = {e.course_id: e.status for e in effective}
        unresolved_failed_last_sem = sum(
            1 for e in enrollments
            if (
                e.semester == last_sem
                and e.status == EnrollmentStatus.failed
                and _is_credit_bearing(e)
                and effective_status_by_course.get(e.course_id) == EnrollmentStatus.failed
            )
        )

    # GPA trend (slope 3 HK gần nhất). Chỉ phần giảm mới là risk signal.
    gpa_trend = calculate_gpa_trend(semester_gpas_list) if semester_gpas_list else 0.0
    gpa_trend_drop = max(0.0, -gpa_trend)

    # Recent semester GPA
    gpa_recent = semester_gpas_list[-1] if semester_gpas_list else 0.0

    # Low GPA streak
    streak = _low_gpa_streak(per_sem_gpa)

    # Attendance
    rates = [e.attendance_rate for e in enrollments if e.attendance_rate is not None]
    avg_attendance = sum(rates) / len(rates) if rates else None

    # Pass rate
    n_finished = sum(
        1 for e in effective
        if _is_credit_bearing(e)
        and e.status in (EnrollmentStatus.passed, EnrollmentStatus.failed)
    )
    pass_rate = (
        sum(
            1 for e in effective
            if _is_credit_bearing(e) and e.status == EnrollmentStatus.passed
        ) / n_finished
        if n_finished > 0 else 1.0
    )
    pass_rate_deficit = 1.0 - pass_rate

    unresolved_failed_retake, recovered_failed = _retake_outcomes(enrollments, effective)

    return {
        "gpa_cumulative_deficit":          _gpa_deficit(student.gpa_cumulative),
        "gpa_recent_deficit":              _gpa_deficit(gpa_recent),
        "gpa_trend_drop":                  _safe(gpa_trend_drop),
        "low_gpa_streak":                  float(streak),
        "unresolved_failed_courses":       float(unresolved_failed),
        "unresolved_failed_last_semester": float(unresolved_failed_last_sem),
        "unresolved_failed_retake_count":  float(unresolved_failed_retake),
        "withdrawn_count":                 float(withdrawn_count),
        "pass_rate_deficit":               _safe(pass_rate_deficit),
        "attendance_risk":                 _attendance_risk(avg_attendance),
        "recovered_failed_courses":        float(recovered_failed),
    }


async def extract_features_for_student_id(
    student_id: UUID,
    db: AsyncSession,
) -> Optional[dict[str, float]]:
    """Helper: fetch student + enrollments rồi gọi extract_features."""
    student = await db.get(Student, student_id)
    if not student:
        return None
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student_id)
        .options(selectinload(Enrollment.course))
    )
    enrollments = result.scalars().all()
    return await extract_features(student, enrollments)


async def extract_features_batch(
    db: AsyncSession,
    only_synthetic: bool = False,
) -> tuple[list[UUID], list[dict[str, float]], list[int]]:
    """
    Extract features cho nhiều SV (dùng để train).
    Return (student_ids, features_list, labels) với label = warning_level >= 1.
    """
    q = select(Student)
    if only_synthetic:
        q = q.where(Student.mssv.like("SYN%"))
    result = await db.execute(q)
    students = result.scalars().all()

    # Eager-load all enrollments grouped by student
    er = await db.execute(
        select(Enrollment).options(selectinload(Enrollment.course))
    )
    all_enrollments = er.scalars().all()
    by_student: dict[UUID, list[Enrollment]] = {}
    for e in all_enrollments:
        by_student.setdefault(e.student_id, []).append(e)

    student_ids: list[UUID] = []
    features_list: list[dict[str, float]] = []
    labels: list[int] = []
    for s in students:
        feats = await extract_features(s, by_student.get(s.id, []))
        student_ids.append(s.id)
        features_list.append(feats)
        labels.append(1 if s.warning_level >= 1 else 0)

    return student_ids, features_list, labels
