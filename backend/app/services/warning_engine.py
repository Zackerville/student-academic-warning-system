"""
Warning Engine — logic core của M6.

Pure functions trước (testable không cần DB), orchestrator gọi DB phía sau.

Quy chế HCMUT (CLAUDE.md ⚠️ Quan trọng):
- Cảnh báo mức 1: GPA tích lũy < 1.2 (thang 4) HOẶC GPA học kỳ < 0.8
- Cảnh báo mức 2: GPA tích lũy < 1.0 HOẶC 2 lần liên tiếp cảnh báo mức 1
- Buộc thôi học (mức 3): GPA tích lũy < 0.8 HOẶC 3 lần cảnh báo HOẶC 2 lần mức 2
- AI Early Warning: risk_score >= AI_EARLY_WARNING_THRESHOLD → cảnh báo sớm
  (không tạo Warning chính thức, chỉ tạo Notification + email với template ai_early_warning)

Idempotent: với (student, semester) đã có Warning cùng level → KHÔNG tạo trùng.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.enrollment import Enrollment
from app.models.notification import Notification, NotificationType
from app.models.prediction import Prediction
from app.models.student import Student
from app.models.user import User
from app.models.warning import Warning, WarningCreatedBy
from app.services import email_service
from app.services.gpa_calculator import EnrollmentGrade, calculate_semester_gpa
from app.services.grade_aggregator import (
    enrollment_gpa_point,
    has_gpa_bearing_grade,
    is_credit_bearing,
    sync_student_stats,
)


# ─── Pure logic ────────────────────────────────────────────────


@dataclass(frozen=True)
class WarningDecision:
    """Output của pure check — caller decide có persist không."""
    level: int  # 0/1/2/3
    reason: str
    triggered_by: str  # "regulation_gpa_cumulative" | "regulation_gpa_semester" | "consecutive" | "none"


def check_regulation_warning(
    *,
    cumulative_gpa: float,
    semester_gpa: Optional[float],
    consecutive_level1_count: int,
    consecutive_level2_count: int,
    total_warnings: int,
) -> WarningDecision:
    """
    Tính level cảnh báo theo quy chế HCMUT.

    Args:
        cumulative_gpa: GPA tích lũy thang 4 hiện tại (sau highest-wins)
        semester_gpa: GPA học kỳ vừa kết thúc (None nếu chưa có)
        consecutive_level1_count: số HK liên tiếp gần nhất bị cảnh báo mức 1
        consecutive_level2_count: số HK liên tiếp gần nhất bị cảnh báo mức 2
        total_warnings: tổng số cảnh báo lịch sử (mọi mức)

    Returns:
        WarningDecision với level 0 (không) / 1 / 2 / 3 (buộc thôi học)
    """
    # Mức 3 — Buộc thôi học (kiểm tra trước vì nghiêm trọng nhất)
    if cumulative_gpa < 0.8:
        return WarningDecision(
            level=3,
            reason=f"GPA tích lũy {cumulative_gpa:.2f} < 0.80 — buộc thôi học theo quy chế HCMUT.",
            triggered_by="regulation_gpa_cumulative",
        )
    if total_warnings >= 3:
        return WarningDecision(
            level=3,
            reason=f"Đã có {total_warnings} lần cảnh báo học vụ — buộc thôi học theo quy chế HCMUT.",
            triggered_by="regulation_gpa_cumulative",
        )
    if consecutive_level2_count >= 2:
        return WarningDecision(
            level=3,
            reason="Bị cảnh báo mức 2 liên tiếp 2 học kỳ — buộc thôi học theo quy chế HCMUT.",
            triggered_by="consecutive",
        )

    # Mức 2 — Cảnh báo nghiêm trọng
    if cumulative_gpa < 1.0:
        return WarningDecision(
            level=2,
            reason=f"GPA tích lũy {cumulative_gpa:.2f} < 1.00 — cảnh báo học vụ mức 2.",
            triggered_by="regulation_gpa_cumulative",
        )
    if consecutive_level1_count >= 2:
        return WarningDecision(
            level=2,
            reason="Bị cảnh báo mức 1 liên tiếp 2 học kỳ — chuyển lên cảnh báo mức 2.",
            triggered_by="consecutive",
        )

    # Mức 1 — Cảnh báo
    if cumulative_gpa < 1.2:
        return WarningDecision(
            level=1,
            reason=f"GPA tích lũy {cumulative_gpa:.2f} < 1.20 — cảnh báo học vụ mức 1.",
            triggered_by="regulation_gpa_cumulative",
        )
    if semester_gpa is not None and semester_gpa < 0.8:
        return WarningDecision(
            level=1,
            reason=f"GPA học kỳ vừa qua {semester_gpa:.2f} < 0.80 — cảnh báo học vụ mức 1.",
            triggered_by="regulation_gpa_semester",
        )

    return WarningDecision(level=0, reason="", triggered_by="none")


def check_ai_early_warning(
    *,
    risk_score: Optional[float],
    threshold: Optional[float] = None,
) -> bool:
    """True nếu risk score AI vượt ngưỡng và SV chưa bị cảnh báo chính thức."""
    if risk_score is None:
        return False
    cutoff = threshold if threshold is not None else settings.AI_EARLY_WARNING_THRESHOLD
    return risk_score >= cutoff


def warning_title(level: int) -> str:
    return {
        1: "Cảnh báo học vụ mức 1",
        2: "Cảnh báo học vụ mức 2",
        3: "Cảnh báo: Nguy cơ buộc thôi học",
    }.get(level, "Cảnh báo học vụ")


def email_subject_for(level: int) -> str:
    return {
        1: "[HCMUT] Cảnh báo học vụ mức 1",
        2: "[HCMUT] Cảnh báo học vụ mức 2 — cần hành động",
        3: "[HCMUT] CẢNH BÁO KHẨN CẤP — Nguy cơ buộc thôi học",
    }.get(level, "[HCMUT] Cảnh báo học vụ")


def email_template_for(level: int) -> str:
    return {1: "warning_level_1", 2: "warning_level_2", 3: "warning_level_3"}.get(
        level, "warning_level_1"
    )


# ─── DB orchestrator ───────────────────────────────────────────


async def _count_consecutive_warnings_at_level(
    db: AsyncSession, student_id: UUID, target_level: int
) -> int:
    """
    Đếm số HK liên tiếp gần nhất có cảnh báo == target_level.
    Dừng đếm khi gặp HK không có cảnh báo (hoặc cảnh báo khác mức).
    """
    result = await db.execute(
        select(Warning)
        .where(Warning.student_id == student_id)
        .order_by(Warning.semester.desc(), Warning.created_at.desc())
        .limit(20)
    )
    warnings = result.scalars().all()

    seen_semesters = set()
    streak = 0
    for w in warnings:
        if w.semester in seen_semesters:
            continue
        seen_semesters.add(w.semester)
        if w.level == target_level:
            streak += 1
        else:
            break
    return streak


async def _has_warning_for_semester(
    db: AsyncSession, student_id: UUID, semester: str, level: int
) -> bool:
    result = await db.execute(
        select(Warning.id).where(
            Warning.student_id == student_id,
            Warning.semester == semester,
            Warning.level == level,
        )
    )
    return result.scalar_one_or_none() is not None


async def _count_total_warnings(db: AsyncSession, student_id: UUID) -> int:
    result = await db.execute(
        select(Warning).where(Warning.student_id == student_id)
    )
    return len(result.scalars().all())


async def _latest_prediction(db: AsyncSession, student_id: UUID) -> Optional[Prediction]:
    result = await db.execute(
        select(Prediction)
        .where(Prediction.student_id == student_id)
        .order_by(Prediction.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _resolve_user_for_student(
    db: AsyncSession, student: Student
) -> Optional[User]:
    """Lazy-load user nếu relationship chưa được load."""
    loaded_user = student.__dict__.get("user")
    if loaded_user is not None:
        return loaded_user
    result = await db.execute(select(User).where(User.id == student.user_id))
    return result.scalar_one_or_none()


async def _load_student_enrollments(db: AsyncSession, student_id: UUID) -> list[Enrollment]:
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student_id)
        .options(selectinload(Enrollment.course))
    )
    return list(result.scalars().all())


def _latest_semester_gpa(enrollments: list[Enrollment]) -> Optional[float]:
    semesters = sorted({e.semester for e in enrollments}, reverse=True)
    for semester in semesters:
        gpa_enrollments = [
            e for e in enrollments
            if e.semester == semester
            and is_credit_bearing(e)
            and enrollment_gpa_point(e) is not None
        ]
        if not gpa_enrollments:
            continue
        return calculate_semester_gpa([
            EnrollmentGrade(
                credits=e.course.credits,
                grade_letter=e.grade_letter,
                total_score=e.total_score,
            )
            for e in gpa_enrollments
        ])
    return None


def _is_cold_start_warning(warning: Warning) -> bool:
    """
    Warning sai sinh ra khi tài khoản chưa có bảng điểm:
    GPA mặc định 0.0 bị hiểu nhầm là GPA học vụ thật.
    """
    return (
        warning.level == 3
        and warning.created_by == WarningCreatedBy.system
        and abs((warning.gpa_at_warning or 0.0) - 0.0) < 1e-9
        and warning.ai_risk_score is None
        and "GPA tích lũy 0.00 < 0.80" in warning.reason
    )


async def cleanup_cold_start_warnings(
    db: AsyncSession,
    student: Student,
    *,
    enrollments: Optional[list[Enrollment]] = None,
) -> int:
    """
    Xoá warning/notification bị tạo sai trước khi SV có dữ liệu điểm.

    Nếu hiện tại SV thật sự vẫn đang ở vùng cảnh báo GPA < 1.2 với dữ liệu điểm
    hợp lệ thì không xoá, vì khi đó warning GPA 0 có thể là lịch sử hợp lệ.
    """
    enrollments = (
        enrollments
        if enrollments is not None
        else await _load_student_enrollments(db, student.id)
    )
    has_real_grades = has_gpa_bearing_grade(enrollments)
    if has_real_grades and (student.gpa_cumulative or 0.0) < 1.2:
        return 0

    result = await db.execute(
        select(Warning).where(Warning.student_id == student.id)
    )
    stale_warnings = [w for w in result.scalars().all() if _is_cold_start_warning(w)]
    if not stale_warnings:
        return 0

    for warning in stale_warnings:
        if warning.notification_id:
            notification = await db.get(Notification, warning.notification_id)
            if notification:
                await db.delete(notification)
        await db.delete(warning)

    await db.commit()
    logger.info(
        f"[warning_engine] Removed {len(stale_warnings)} cold-start warning(s) for student={student.mssv}"
    )
    return len(stale_warnings)


async def current_warning_decision(
    db: AsyncSession,
    student: Student,
    *,
    semester_gpa: Optional[float] = None,
) -> WarningDecision:
    """
    Recompute trạng thái cảnh báo hiện tại từ dữ liệu học vụ đang có.

    Tài khoản mới chưa có điểm có GPA mặc định 0.0, nhưng không được xem là
    GPA học vụ thật. Vì vậy case chưa có môn GPA-bearing luôn trả level 0.
    """
    await sync_student_stats(student, db)
    await db.refresh(student)

    enrollments = await _load_student_enrollments(db, student.id)
    await cleanup_cold_start_warnings(db, student, enrollments=enrollments)

    if not has_gpa_bearing_grade(enrollments):
        return WarningDecision(
            level=0,
            reason="Chưa có dữ liệu điểm học vụ để xét cảnh báo.",
            triggered_by="none",
        )

    if semester_gpa is None:
        semester_gpa = _latest_semester_gpa(enrollments)

    consecutive_l1 = await _count_consecutive_warnings_at_level(db, student.id, 1)
    consecutive_l2 = await _count_consecutive_warnings_at_level(db, student.id, 2)
    total_warnings = await _count_total_warnings(db, student.id)

    return check_regulation_warning(
        cumulative_gpa=student.gpa_cumulative or 0.0,
        semester_gpa=semester_gpa,
        consecutive_level1_count=consecutive_l1,
        consecutive_level2_count=consecutive_l2,
        total_warnings=total_warnings,
    )


async def sync_current_warning_level(
    db: AsyncSession,
    student: Student,
    *,
    semester_gpa: Optional[float] = None,
) -> WarningDecision:
    """Persist student.warning_level theo trạng thái hiện tại."""
    decision = await current_warning_decision(
        db, student, semester_gpa=semester_gpa
    )
    student.warning_level = decision.level
    await db.commit()
    await db.refresh(student)
    return decision


@dataclass
class WarningOutcome:
    """Kết quả của evaluate_and_persist — caller dùng để toast FE."""
    created: bool
    warning: Optional[Warning] = None
    notification: Optional[Notification] = None
    decision: Optional[WarningDecision] = None
    ai_early_warning: bool = False


async def evaluate_and_persist(
    *,
    db: AsyncSession,
    student: Student,
    semester: str,
    semester_gpa: Optional[float] = None,
    triggered_by: str = "auto",
) -> WarningOutcome:
    """
    Orchestrator — gọi từ batch job + grade-update hook + admin trigger.

    Steps:
    1) Aggregate state SV (cumulative_gpa từ student model — assume đã sync)
    2) Count consecutive level1/level2 từ history
    3) Pure check_regulation_warning → WarningDecision
    4) Nếu level > 0 và chưa có warning cùng (semester, level) → tạo Warning + Notification
       + spawn email (fire-and-forget, fail-soft)
    5) Nếu level == 0 → check AI early warning từ latest prediction
    6) Return WarningOutcome (created=False nếu idempotent)
    """
    decision = await current_warning_decision(
        db, student, semester_gpa=semester_gpa
    )

    if decision.level == 0:
        student.warning_level = 0
        await db.commit()

        # No regulation warning — check AI early warning
        prediction = await _latest_prediction(db, student.id)
        ai_score = prediction.risk_score if prediction else None
        if check_ai_early_warning(risk_score=ai_score):
            await _create_ai_early_warning_notification(
                db, student, prediction, semester
            )
            return WarningOutcome(
                created=False, decision=decision, ai_early_warning=True
            )
        return WarningOutcome(created=False, decision=decision)

    if await _has_warning_for_semester(db, student.id, semester, decision.level):
        student.warning_level = decision.level
        await db.commit()
        logger.info(
            f"[warning_engine] Idempotent skip — student={student.mssv} sem={semester} level={decision.level}"
        )
        return WarningOutcome(created=False, decision=decision)

    user = await _resolve_user_for_student(db, student)

    notification = Notification(
        student_id=student.id,
        type=NotificationType.warning,
        title=warning_title(decision.level),
        content=decision.reason,
    )
    db.add(notification)
    await db.flush()

    warning = Warning(
        student_id=student.id,
        level=decision.level,
        semester=semester,
        reason=decision.reason,
        gpa_at_warning=student.gpa_cumulative or 0.0,
        ai_risk_score=None,
        is_resolved=False,
        sent_at=datetime.now(tz=timezone.utc),
        notification_id=notification.id,
        created_by=WarningCreatedBy.system if triggered_by != "admin" else WarningCreatedBy.admin,
    )
    db.add(warning)

    # Cập nhật student.warning_level về mức cao nhất hiện tại
    student.warning_level = decision.level
    await db.commit()
    await db.refresh(warning)
    await db.refresh(notification)

    # Fire email (fail-soft, không block)
    if user and user.email_notifications_enabled and user.email and "@" in user.email:
        email_service.fire_and_forget(
            to=user.email,
            subject=email_subject_for(decision.level),
            template_name=email_template_for(decision.level),
            context={
                "full_name": student.full_name,
                "mssv": student.mssv,
                "semester": semester,
                "gpa_cumulative": student.gpa_cumulative or 0.0,
                "gpa_semester": semester_gpa,
                "reason": decision.reason,
            },
        )
        notification.email_sent_at = datetime.now(tz=timezone.utc)
        await db.commit()

    logger.info(
        f"[warning_engine] Created level={decision.level} for student={student.mssv} sem={semester}"
    )
    return WarningOutcome(
        created=True, warning=warning, notification=notification, decision=decision
    )


async def _create_ai_early_warning_notification(
    db: AsyncSession,
    student: Student,
    prediction: Prediction,
    semester: str,
) -> None:
    """
    Tạo notification riêng cho AI early warning (không tạo Warning row chính thức).
    Idempotent: 1 SV chỉ có 1 AI early warning trong 7 ngày gần nhất.
    """
    from datetime import timedelta

    week_ago = datetime.now(tz=timezone.utc) - timedelta(days=7)
    result = await db.execute(
        select(Notification)
        .where(
            Notification.student_id == student.id,
            Notification.type == NotificationType.warning,
            Notification.title.like("%dự báo%"),
            Notification.created_at >= week_ago,
        )
        .limit(1)
    )
    if result.scalar_one_or_none():
        return  # Đã có trong 7 ngày, skip

    risk_pct = int((prediction.risk_score or 0) * 100)
    risk_level_vi = {
        "low": "thấp",
        "medium": "trung bình",
        "high": "cao",
        "critical": "rất cao",
    }.get(getattr(prediction.risk_level, "value", str(prediction.risk_level)), "trung bình")

    notification = Notification(
        student_id=student.id,
        type=NotificationType.warning,
        title=f"AI dự báo nguy cơ học vụ ({risk_pct}%)",
        content=(
            f"Hệ thống AI dự báo bạn đang có nguy cơ rơi vào diện cảnh báo học vụ. "
            f"Risk score {risk_pct}% (mức {risk_level_vi}). "
            f"Vào trang Dự báo sớm để xem chi tiết phân tích và lý do."
        ),
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    user = await _resolve_user_for_student(db, student)
    if user and user.email_notifications_enabled and user.email and "@" in user.email:
        top_factors = []
        if prediction.risk_factors:
            factors = prediction.risk_factors
            if isinstance(factors, dict):
                items = factors.get("top_factors") or factors.get("factors") or []
                top_factors = [
                    str(f.get("description") or f.get("name") or f)
                    for f in items[:3]
                ]
        email_service.fire_and_forget(
            to=user.email,
            subject="[HCMUT] Dự báo nguy cơ học vụ từ AI",
            template_name="ai_early_warning",
            context={
                "full_name": student.full_name,
                "mssv": student.mssv,
                "risk_score": prediction.risk_score or 0.0,
                "risk_level_vi": risk_level_vi,
                "gpa_cumulative": student.gpa_cumulative or 0.0,
                "top_factors": top_factors,
            },
        )
        notification.email_sent_at = datetime.now(tz=timezone.utc)
        await db.commit()


async def batch_check_warnings(db: AsyncSession, semester: str) -> dict[str, int]:
    """
    Batch check tất cả SV active — gọi từ scheduler hoặc admin trigger.
    Idempotent: skip SV đã có cảnh báo cùng semester+level.
    """
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.user))
    )
    students = result.scalars().all()

    stats = {"checked": 0, "created": 0, "ai_early": 0, "skipped": 0}
    for student in students:
        stats["checked"] += 1
        try:
            outcome = await evaluate_and_persist(
                db=db, student=student, semester=semester
            )
            if outcome.created:
                stats["created"] += 1
            elif outcome.ai_early_warning:
                stats["ai_early"] += 1
            else:
                stats["skipped"] += 1
        except Exception as exc:
            logger.error(
                f"[warning_engine.batch] student={student.mssv} failed: {exc}"
            )

    logger.info(f"[warning_engine.batch] semester={semester} stats={stats}")
    return stats
