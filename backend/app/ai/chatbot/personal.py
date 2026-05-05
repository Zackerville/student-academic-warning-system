"""
Build student context cho RAG chatbot — inject GPA/warning/F-courses vào prompt.

> CONTRACT: format text trả về phải khớp regex parsers trong
> `app.ai.chatbot.providers.ExtractiveChatProvider._parse_student_context`.
> Nếu thay đổi label tiếng Việt ở `lines = [...]` bên dưới thì PHẢI update
> regex tương ứng để fallback "no API key" không trả answer rỗng.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.prediction import Prediction
from app.models.student import Student
from app.services.grade_aggregator import (
    effective_enrollments_per_course,
    enrollment_gpa_point,
)


async def build_student_context(student: Student, db: AsyncSession) -> str:
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student.id)
        .options(selectinload(Enrollment.course))
        .order_by(Enrollment.semester.desc())
    )
    enrollments = result.scalars().all()

    latest_prediction = await db.scalar(
        select(Prediction)
        .where(Prediction.student_id == student.id)
        .order_by(Prediction.created_at.desc())
        .limit(1)
    )

    semesters = sorted({item.semester for item in enrollments}, reverse=True)
    failed_attempts = [
        item for item in enrollments
        if item.status == EnrollmentStatus.failed and item.course and item.course.credits > 0
    ]
    effective_enrollments = effective_enrollments_per_course(enrollments)
    latest_enrollments = _latest_enrollments_per_course(enrollments)
    unresolved_failed = [
        item for item in effective_enrollments
        if item.status == EnrollmentStatus.failed and item.course and item.course.credits > 0
    ]
    resolved_failed = _resolved_failed_attempts(failed_attempts, effective_enrollments)
    current_semester = semesters[0] if semesters else "chưa có"
    current_courses = [item for item in enrollments if item.semester == current_semester]
    imported_sources = sorted({item.source for item in enrollments if item.source})
    improvement_candidates = _improvement_candidates(latest_enrollments)

    lines = [
        f"- Sinh viên: {student.full_name} ({student.mssv}), ngành {student.major}, khóa {student.cohort}.",
        f"- GPA tích lũy hiện lưu: {student.gpa_cumulative:.2f}; tín chỉ tích lũy: {student.credits_earned}; cảnh báo mức: {student.warning_level}.",
        (
            "- Bảng điểm đã parse từ page Điểm số đang có trong database: "
            f"{len(enrollments)} lượt học, {len(latest_enrollments)} môn theo lần học mới nhất; "
            f"nguồn dữ liệu: {', '.join(imported_sources) if imported_sources else 'chưa rõ'}. "
            "Chatbot được phép dùng dữ liệu này để tư vấn, dù không mở lại file/raw text MyBK ban đầu."
        ),
        f"- Học kỳ gần nhất trong dữ liệu: {current_semester}; số môn ở học kỳ này: {len(current_courses)}.",
        f"- Các môn ở học kỳ gần nhất: {_format_course_list(current_courses) if current_courses else 'không có'}.",
        f"- Lượt F lịch sử trong dữ liệu: {len(failed_attempts)}.",
        f"- Môn chưa đạt còn hiệu lực: {_format_course_list(unresolved_failed) if unresolved_failed else 'không có'}.",
    ]

    if improvement_candidates:
        lines.append(
            "- Môn điểm thấp/có thể cân nhắc cải thiện theo bảng điểm đã parse: "
            f"{_format_course_list(improvement_candidates, include_points=True)}."
        )

    if failed_attempts:
        lines.append(f"- Các lượt F lịch sử: {_format_course_list(failed_attempts)}.")

    if resolved_failed:
        lines.append(f"- Môn từng F nhưng đã có lần học sau đạt/tốt hơn: {', '.join(resolved_failed[:8])}.")

    if latest_prediction:
        lines.append(
            f"- Dự báo AI gần nhất: risk score {latest_prediction.risk_score:.1%}, mức {latest_prediction.risk_level.value}."
        )

    return "\n".join(lines)


def _latest_enrollments_per_course(enrollments: list[Enrollment]) -> list[Enrollment]:
    by_course: dict = {}
    for enrollment in enrollments:
        is_in_progress = (
            enrollment.status == EnrollmentStatus.enrolled
            and not enrollment.grade_letter
            and enrollment.total_score is None
        )
        if is_in_progress:
            continue
        current = by_course.get(enrollment.course_id)
        if current is None or enrollment.semester > current.semester:
            by_course[enrollment.course_id] = enrollment
    return list(by_course.values())


def _resolved_failed_attempts(
    failed_attempts: list[Enrollment],
    effective_enrollments: list[Enrollment],
) -> list[str]:
    effective_by_course = {item.course_id: item for item in effective_enrollments}
    resolved: list[str] = []
    for failed in failed_attempts:
        effective = effective_by_course.get(failed.course_id)
        if not effective or effective.id == failed.id or effective.status == EnrollmentStatus.failed:
            continue
        failed_grade = failed.grade_letter or failed.total_score or "F"
        effective_grade = effective.grade_letter or effective.total_score or effective.status.value
        resolved.append(
            f"{failed.course.course_code} ({failed_grade} HK{failed.semester} -> {effective_grade} HK{effective.semester})"
        )
    return resolved


def _improvement_candidates(enrollments: list[Enrollment]) -> list[Enrollment]:
    candidates = []
    for enrollment in enrollments:
        if not enrollment.course or enrollment.course.credits <= 0:
            continue
        point = enrollment_gpa_point(enrollment)
        if point is None:
            continue
        if enrollment.status == EnrollmentStatus.failed or point <= 2.5:
            candidates.append((enrollment, point))

    candidates.sort(
        key=lambda item: (
            item[1],
            -item[0].course.credits,
            item[0].semester,
            item[0].course.course_code,
        )
    )
    return [item for item, _point in candidates[:12]]


def _format_course_list(enrollments: list[Enrollment], *, include_points: bool = False) -> str:
    items = []
    for enrollment in enrollments[:10]:
        grade = enrollment.grade_letter or enrollment.total_score or enrollment.status.value
        point = enrollment_gpa_point(enrollment)
        point_text = f", hệ 4 {point:.1f}" if include_points and point is not None else ""
        items.append(
            f"{enrollment.course.course_code} - {enrollment.course.name} "
            f"({enrollment.course.credits} TC, {grade}{point_text}, HK{enrollment.semester})"
        )
    return ", ".join(items)
