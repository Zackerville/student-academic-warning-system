"""Admin endpoints (M7).

Toàn bộ endpoint require admin role. Không trả dữ liệu cá nhân nhạy cảm
(hashed_password) ra ngoài.
"""
from __future__ import annotations

import io
from collections import Counter
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.deps import require_admin
from app.db.session import get_db
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.notification import NotificationType
from app.models.prediction import Prediction
from app.models.student import Student
from app.models.user import User
from app.models.warning import Warning, WarningCreatedBy
from app.schemas.admin import (
    AdminDashboardStats,
    AdminManualWarningCreate,
    AdminStatistics,
    AdminStudentDetail,
    AdminStudentListItem,
    AdminStudentListResponse,
    AdminWarningSummary,
    ApprovePendingPayload,
    FacultyWarningBucket,
    GpaDistributionBucket,
    GpaHistoryPoint,
    ImportHistoryItem,
    ImportResult,
    PendingWarningItem,
    PendingWarningsResponse,
    PassFailBucket,
    RiskBucket,
    RiskDistributionBucket,
    SemesterWarningCount,
    ThresholdConfig,
    TopRiskStudent,
    WarningLevelReportBucket,
    WarningLevelBucket,
)
from app.services import import_service
from app.services.gpa_calculator import EnrollmentGrade, calculate_semester_gpa
from app.services.grade_aggregator import (
    count_unresolved_failed,
    effective_enrollments_per_course,
    enrollment_gpa_point,
    sync_student_stats,
)
from app.services.notification import create as create_notification
from app.services.warning_engine import batch_check_warnings


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ─── Helpers ────────────────────────────────────────────────

async def _latest_predictions_map(db: AsyncSession, student_ids: list[UUID]) -> dict[UUID, Prediction]:
    """Return dict student_id -> latest Prediction. Empty if no ids."""
    if not student_ids:
        return {}
    subq = (
        select(
            Prediction.student_id,
            func.max(Prediction.created_at).label("max_at"),
        )
        .where(Prediction.student_id.in_(student_ids))
        .group_by(Prediction.student_id)
        .subquery()
    )
    rows = (await db.execute(
        select(Prediction).join(
            subq,
            and_(
                Prediction.student_id == subq.c.student_id,
                Prediction.created_at == subq.c.max_at,
            ),
        )
    )).scalars().all()
    return {p.student_id: p for p in rows}


def _risk_bucket(score: float) -> str:
    if score >= 0.8: return "critical"
    if score >= 0.6: return "high"
    if score >= 0.3: return "medium"
    return "low"


RISK_LABELS = {
    "low": "Thấp",
    "medium": "Trung bình",
    "high": "Cao",
    "critical": "Nghiêm trọng",
    "none": "Chưa dự báo",
}

WARNING_LEVEL_LABELS = {
    0: "Bình thường",
    1: "Mức 1",
    2: "Mức 2",
    3: "Buộc thôi học",
}


# ─── Dashboard ──────────────────────────────────────────────

@router.get("/dashboard", response_model=AdminDashboardStats)
async def get_admin_dashboard(db: AsyncSession = Depends(get_db)):
    students = (await db.execute(select(Student))).scalars().all()
    student_ids = [s.id for s in students]
    preds = await _latest_predictions_map(db, student_ids)

    # By warning level
    level_counter: Counter[int] = Counter()
    for s in students:
        level_counter[s.warning_level] += 1
    by_warning_level = [
        WarningLevelBucket(level=lvl, count=level_counter.get(lvl, 0))
        for lvl in (0, 1, 2, 3)
    ]

    # By risk level (predictions)
    risk_counter: Counter[str] = Counter()
    for s in students:
        p = preds.get(s.id)
        bucket = _risk_bucket(p.risk_score) if p else "low"
        risk_counter[bucket] += 1
    risk_labels = {
        "low": "Thấp", "medium": "TB", "high": "Cao", "critical": "Nghiêm trọng"
    }
    by_risk_level = [
        RiskBucket(bucket=b, count=risk_counter.get(b, 0), label_vi=risk_labels[b])  # type: ignore[arg-type]
        for b in ("low", "medium", "high", "critical")
    ]

    # By faculty
    faculty_total: Counter[str] = Counter()
    faculty_warned: Counter[str] = Counter()
    for s in students:
        faculty_total[s.faculty] += 1
        if s.warning_level >= 1:
            faculty_warned[s.faculty] += 1
    by_faculty = []
    for faculty, total in faculty_total.most_common():
        warned = faculty_warned.get(faculty, 0)
        pct = round(warned / total * 100, 1) if total else 0.0
        by_faculty.append(FacultyWarningBucket(
            faculty=faculty, warning_count=warned, total_students=total, pct=pct,
        ))

    # Top risk
    sortable = []
    for s in students:
        p = preds.get(s.id)
        score = p.risk_score if p else 0.0
        sortable.append((score, s, p))
    sortable.sort(key=lambda x: x[0], reverse=True)
    top_risk: list[TopRiskStudent] = []
    for score, s, p in sortable[:10]:
        if score <= 0:
            break
        top_risk.append(TopRiskStudent(
            student_id=s.id, mssv=s.mssv, full_name=s.full_name, faculty=s.faculty,
            gpa_cumulative=s.gpa_cumulative, warning_level=s.warning_level,
            risk_score=score if p else None,
            risk_level=p.risk_level.value if p else None,
        ))

    total_warned = sum(1 for s in students if s.warning_level >= 1)
    total_high_risk = sum(1 for s in students if (preds.get(s.id) and preds[s.id].risk_score >= 0.6))
    total_critical = sum(1 for s in students if (preds.get(s.id) and preds[s.id].risk_score >= 0.8))

    return AdminDashboardStats(
        total_students=len(students),
        total_warned=total_warned,
        total_high_risk=total_high_risk,
        total_critical=total_critical,
        by_warning_level=by_warning_level,
        by_risk_level=by_risk_level,
        by_faculty=by_faculty[:10],
        top_risk=top_risk,
        generated_at=datetime.now(timezone.utc),
    )


# ─── Students list ──────────────────────────────────────────

@router.get("/students", response_model=AdminStudentListResponse)
async def list_students(
    db: AsyncSession = Depends(get_db),
    q: Optional[str] = Query(None, description="Search MSSV / name / email"),
    faculty: Optional[str] = None,
    cohort: Optional[int] = None,
    warning_level: Optional[int] = Query(None, ge=0, le=3),
    high_risk: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
):
    stmt = select(Student, User).join(User, Student.user_id == User.id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(
            Student.mssv.ilike(like),
            Student.full_name.ilike(like),
            User.email.ilike(like),
        ))
    if faculty:
        stmt = stmt.where(Student.faculty == faculty)
    if cohort is not None:
        stmt = stmt.where(Student.cohort == cohort)
    if warning_level is not None:
        stmt = stmt.where(Student.warning_level == warning_level)

    rows = (await db.execute(stmt.order_by(Student.mssv))).all()

    # latest predictions for filter + display
    student_ids = [s.id for s, _u in rows]
    preds = await _latest_predictions_map(db, student_ids)

    items: list[AdminStudentListItem] = []
    for s, u in rows:
        p = preds.get(s.id)
        if high_risk and not (p and p.risk_score >= 0.6):
            continue
        items.append(AdminStudentListItem(
            student_id=s.id, mssv=s.mssv, full_name=s.full_name,
            faculty=s.faculty, major=s.major, cohort=s.cohort, email=u.email,
            gpa_cumulative=s.gpa_cumulative, credits_earned=s.credits_earned,
            warning_level=s.warning_level,
            risk_score=p.risk_score if p else None,
            risk_level=p.risk_level.value if p else None,
        ))

    total = len(items)
    start = (page - 1) * size
    paged = items[start:start + size]
    return AdminStudentListResponse(items=paged, total=total, page=page, size=size)


# ─── Student detail ─────────────────────────────────────────

@router.get("/students/{student_id}", response_model=AdminStudentDetail)
async def get_student_detail(student_id: UUID, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(
        select(Student, User).join(User, Student.user_id == User.id)
        .where(Student.id == student_id)
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên")
    student, user = row

    # Sync stats first (mutates student in-place, no return value)
    await sync_student_stats(student, db)

    # Load enrollments + courses for history + failed count
    enroll_rows = (await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student.id)
        .options(selectinload(Enrollment.course))
    )).scalars().all()

    failed_total = count_unresolved_failed(effective_enrollments_per_course(list(enroll_rows)))

    # GPA history per semester (inline, mirrors students.py /me/gpa/history)
    semester_map: dict[str, list[Enrollment]] = {}
    for e in enroll_rows:
        semester_map.setdefault(e.semester, []).append(e)
    gpa_history: list[GpaHistoryPoint] = []
    for sem in sorted(semester_map.keys()):
        sem_enrolls = [e for e in semester_map[sem] if e.course.credits > 0]
        if not sem_enrolls:
            continue
        grades = [
            EnrollmentGrade(
                credits=e.course.credits,
                grade_letter=e.grade_letter,
                total_score=e.total_score,
            )
            for e in sem_enrolls
        ]
        gpa_history.append(GpaHistoryPoint(
            semester=sem,
            semester_gpa=calculate_semester_gpa(grades),
            credits_taken=sum(e.course.credits for e in sem_enrolls),
            courses_count=len(sem_enrolls),
        ))

    # Latest prediction
    pred = (await _latest_predictions_map(db, [student.id])).get(student.id)
    risk_factors = []
    if pred and pred.risk_factors:
        if isinstance(pred.risk_factors, dict):
            risk_factors = pred.risk_factors.get("factors", [])
        elif isinstance(pred.risk_factors, list):
            risk_factors = pred.risk_factors

    # Warnings
    warns = (await db.execute(
        select(Warning).where(Warning.student_id == student.id).order_by(Warning.sent_at.desc().nullslast())
    )).scalars().all()
    warnings_summary = [
        AdminWarningSummary(
            id=w.id, level=w.level, semester=w.semester, reason=w.reason,
            gpa_at_warning=w.gpa_at_warning, is_resolved=w.is_resolved,
            sent_at=w.sent_at, created_by=w.created_by.value,
        )
        for w in warns
    ]

    return AdminStudentDetail(
        student_id=student.id, mssv=student.mssv, full_name=student.full_name,
        faculty=student.faculty, major=student.major, cohort=student.cohort,
        email=user.email, is_active=user.is_active,
        gpa_cumulative=student.gpa_cumulative,
        credits_earned=student.credits_earned,
        warning_level=student.warning_level,
        failed_courses_total=failed_total,
        gpa_history=gpa_history,
        risk_score=pred.risk_score if pred else None,
        risk_level=pred.risk_level.value if pred else None,
        risk_factors=risk_factors,
        warnings=warnings_summary,
    )


# ─── Pending warnings (AI suggestions) ──────────────────────

@router.get("/warnings/pending", response_model=PendingWarningsResponse)
async def list_pending_warnings(
    db: AsyncSession = Depends(get_db),
    semester: Optional[str] = None,
):
    threshold = settings.AI_EARLY_WARNING_THRESHOLD
    target_semester = semester or _infer_current_semester()

    # Latest predictions
    students = (await db.execute(select(Student))).scalars().all()
    preds = await _latest_predictions_map(db, [s.id for s in students])

    # Existing warnings for the semester (skip if SV đã có warning HK này)
    existing = {
        (w.student_id, w.semester, w.level)
        for w in (await db.execute(
            select(Warning).where(Warning.semester == target_semester)
        )).scalars().all()
    }

    items: list[PendingWarningItem] = []
    last_batch_at: Optional[datetime] = None
    for s in students:
        p = preds.get(s.id)
        if not p or p.risk_score < threshold:
            continue
        # Suggest level by risk band
        if p.risk_score >= 0.85: suggested_level = 3
        elif p.risk_score >= 0.7: suggested_level = 2
        else: suggested_level = 1
        if (s.id, target_semester, suggested_level) in existing:
            continue
        items.append(PendingWarningItem(
            student_id=s.id, mssv=s.mssv, full_name=s.full_name,
            faculty=s.faculty, semester=target_semester,
            suggested_level=suggested_level, risk_score=p.risk_score,
            risk_level=p.risk_level.value,
            reason=f"Risk score {int(p.risk_score * 100)}% — GPA {s.gpa_cumulative:.2f}",
            gpa_cumulative=s.gpa_cumulative,
        ))
        if last_batch_at is None or p.created_at > last_batch_at:
            last_batch_at = p.created_at

    items.sort(key=lambda x: x.risk_score, reverse=True)
    return PendingWarningsResponse(
        items=items, total=len(items), threshold=threshold,
        last_batch_at=last_batch_at,
    )


def _infer_current_semester() -> str:
    """Best-effort: chọn semester gần nhất từ Prediction; fallback hardcode."""
    return getattr(settings, "CURRENT_SEMESTER", None) or "241"


# ─── Approve pending → create warning ───────────────────────

@router.post("/warnings/approve", response_model=AdminWarningSummary)
async def approve_pending_warning(
    payload: ApprovePendingPayload,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    student = (await db.execute(
        select(Student).where(Student.id == payload.student_id)
    )).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên")

    # idempotency
    existing = (await db.execute(
        select(Warning).where(
            Warning.student_id == student.id,
            Warning.semester == payload.semester,
            Warning.level == payload.level,
        )
    )).scalar_one_or_none()
    if existing:
        return _to_summary(existing)

    pred = (await _latest_predictions_map(db, [student.id])).get(student.id)
    reason = payload.reason or (
        f"Risk score {int(pred.risk_score * 100)}% — GPA {student.gpa_cumulative:.2f}"
        if pred else f"GPA {student.gpa_cumulative:.2f} — admin duyệt"
    )

    warning = Warning(
        student_id=student.id,
        level=payload.level,
        semester=payload.semester,
        reason=reason,
        gpa_at_warning=student.gpa_cumulative,
        ai_risk_score=pred.risk_score if pred else None,
        is_resolved=False,
        sent_at=datetime.now(timezone.utc),
        created_by=WarningCreatedBy.admin,
    )
    db.add(warning)
    await db.flush()

    if student.warning_level < payload.level:
        student.warning_level = payload.level

    # Need student with user relationship loaded for notification email dispatch
    student_full = (await db.execute(
        select(Student).where(Student.id == student.id).options(selectinload(Student.user))
    )).scalar_one()

    notif = await create_notification(
        db=db,
        student=student_full,
        type=NotificationType.warning,
        title=f"Cảnh báo học vụ Mức {payload.level} — HK {payload.semester}",
        content=reason,
        email_template=f"warning_level_{payload.level}.html",
        email_subject=f"[HCMUT] Cảnh báo học vụ Mức {payload.level} — HK {payload.semester}",
        email_context={
            "student_name": student.full_name,
            "level": payload.level,
            "semester": payload.semester,
            "reason": reason,
            "gpa": student.gpa_cumulative,
        },
    )
    if notif:
        warning.notification_id = notif.id

    await db.commit()
    return _to_summary(warning)


# ─── Manual warning create ──────────────────────────────────

@router.post("/warnings/manual", response_model=AdminWarningSummary)
async def create_manual_warning(
    payload: AdminManualWarningCreate,
    db: AsyncSession = Depends(get_db),
):
    student = (await db.execute(
        select(Student).where(Student.id == payload.student_id).options(selectinload(Student.user))
    )).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên")

    warning = Warning(
        student_id=student.id,
        level=payload.level,
        semester=payload.semester,
        reason=payload.reason,
        gpa_at_warning=student.gpa_cumulative,
        ai_risk_score=None,
        is_resolved=False,
        sent_at=datetime.now(timezone.utc),
        created_by=WarningCreatedBy.admin,
    )
    db.add(warning)
    await db.flush()

    if student.warning_level < payload.level:
        student.warning_level = payload.level

    notif = await create_notification(
        db=db,
        student=student,
        type=NotificationType.warning,
        title=f"Cảnh báo học vụ Mức {payload.level} — HK {payload.semester}",
        content=payload.reason,
        email_template=f"warning_level_{payload.level}.html",
        email_subject=f"[HCMUT] Cảnh báo học vụ Mức {payload.level} — HK {payload.semester}",
        email_context={
            "student_name": student.full_name,
            "level": payload.level,
            "semester": payload.semester,
            "reason": payload.reason,
            "gpa": student.gpa_cumulative,
        },
    )
    if notif:
        warning.notification_id = notif.id

    await db.commit()
    return _to_summary(warning)


# ─── Run batch warnings ─────────────────────────────────────

@router.post("/warnings/batch")
async def run_batch_warnings(
    db: AsyncSession = Depends(get_db),
    semester: Optional[str] = Query(None),
):
    target = semester or _infer_current_semester()
    result = await batch_check_warnings(db, semester=target)
    return {"data": result, "message": "Batch warnings completed"}


def _to_summary(w: Warning) -> AdminWarningSummary:
    return AdminWarningSummary(
        id=w.id, level=w.level, semester=w.semester, reason=w.reason,
        gpa_at_warning=w.gpa_at_warning, is_resolved=w.is_resolved,
        sent_at=w.sent_at, created_by=w.created_by.value,
    )


# ─── Import endpoints ───────────────────────────────────────

@router.post("/import/students", response_model=ImportResult)
async def import_students_endpoint(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xlsx")
    content = await file.read()
    return await import_service.import_students(
        db, file_bytes=content, filename=file.filename, uploader_email=admin.email,
    )


@router.post("/import/grades", response_model=ImportResult)
async def import_grades_endpoint(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xlsx")
    content = await file.read()
    return await import_service.import_grades(
        db, file_bytes=content, filename=file.filename, uploader_email=admin.email,
    )


@router.get("/import/templates/students")
async def download_students_template():
    data = import_service.build_students_template()
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="template_students.xlsx"'},
    )


@router.get("/import/templates/grades")
async def download_grades_template():
    data = import_service.build_grades_template()
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="template_grades.xlsx"'},
    )


@router.get("/import/history", response_model=list[ImportHistoryItem])
async def import_history():
    return import_service.get_history()


# ─── Statistics ─────────────────────────────────────────────

@router.get("/statistics", response_model=AdminStatistics)
async def get_statistics(db: AsyncSession = Depends(get_db)):
    students = (await db.execute(select(Student))).scalars().all()
    total = len(students)
    if total == 0:
        return AdminStatistics(
            gpa_average=0.0, warning_rate_pct=0.0, improvement_rate_pct=None,
            pass_rate_pct=None, total_students=0,
            by_semester=[], gpa_distribution=[], semester_now=None,
        )

    student_ids = [s.id for s in students]
    preds = await _latest_predictions_map(db, student_ids)
    gpa_avg = sum(s.gpa_cumulative for s in students) / total
    warned = sum(1 for s in students if s.warning_level >= 1)
    warning_rate = warned / total * 100
    total_high_risk = sum(1 for p in preds.values() if p.risk_score >= 0.6)
    total_critical = sum(1 for p in preds.values() if p.risk_score >= 0.8)

    enrollments = (await db.execute(
        select(Enrollment).options(selectinload(Enrollment.course))
    )).scalars().all()
    enrollment_semesters = sorted({e.semester for e in enrollments})
    latest_sem = enrollment_semesters[-1] if enrollment_semesters else None

    # Warning by semester (last 6, keep latest semester visible even if count=0)
    sem_counter: Counter[str] = Counter()
    for w in (await db.execute(select(Warning))).scalars().all():
        sem_counter[w.semester] += 1
    semester_keys = set(sem_counter.keys())
    if latest_sem:
        semester_keys.add(latest_sem)
    by_semester = [
        SemesterWarningCount(semester=s, count=sem_counter.get(s, 0))
        for s in sorted(semester_keys)[-6:]
    ]

    # GPA distribution
    buckets = {"<1.5": 0, "1.5-2.0": 0, "2.0-2.5": 0, "2.5-3.0": 0, "3.0-3.5": 0, ">3.5": 0}
    for s in students:
        g = s.gpa_cumulative
        if g < 1.5: buckets["<1.5"] += 1
        elif g < 2.0: buckets["1.5-2.0"] += 1
        elif g < 2.5: buckets["2.0-2.5"] += 1
        elif g < 3.0: buckets["2.5-3.0"] += 1
        elif g < 3.5: buckets["3.0-3.5"] += 1
        else: buckets[">3.5"] += 1
    distribution = [GpaDistributionBucket(bucket=b, count=c) for b, c in buckets.items()]

    # Warning level distribution
    level_counter = Counter(s.warning_level for s in students)
    by_warning_level = [
        WarningLevelReportBucket(
            level=level,
            label=WARNING_LEVEL_LABELS[level],
            count=level_counter.get(level, 0),
            pct=round(level_counter.get(level, 0) / total * 100, 1),
        )
        for level in (0, 1, 2, 3)
    ]

    # AI risk distribution
    risk_counter: Counter[str] = Counter()
    for s in students:
        p = preds.get(s.id)
        risk_counter[_risk_bucket(p.risk_score) if p else "none"] += 1
    risk_distribution = [
        RiskDistributionBucket(
            bucket=bucket,
            label_vi=RISK_LABELS[bucket],
            count=risk_counter.get(bucket, 0),
            pct=round(risk_counter.get(bucket, 0) / total * 100, 1),
        )
        for bucket in ("none", "low", "medium", "high", "critical")
    ]

    # Faculty warning rate
    faculty_total: Counter[str] = Counter()
    faculty_warned: Counter[str] = Counter()
    for s in students:
        faculty_total[s.faculty] += 1
        if s.warning_level >= 1:
            faculty_warned[s.faculty] += 1
    by_faculty = [
        FacultyWarningBucket(
            faculty=faculty,
            warning_count=faculty_warned.get(faculty, 0),
            total_students=count,
            pct=round(faculty_warned.get(faculty, 0) / count * 100, 1) if count else 0.0,
        )
        for faculty, count in faculty_total.most_common(8)
    ]

    # Pass rate (latest enrollment semester)
    pass_rate: Optional[float] = None
    latest_pass_fail: list[PassFailBucket] = []
    if latest_sem:
        latest_enrolls = [e for e in enrollments if e.semester == latest_sem]
        finished = [e for e in latest_enrolls if e.status in (EnrollmentStatus.passed, EnrollmentStatus.failed)]
        if finished:
            passed = sum(1 for e in finished if e.status == EnrollmentStatus.passed)
            failed = len(finished) - passed
            pass_rate = round(passed / len(finished) * 100, 1)
            latest_pass_fail = [
                PassFailBucket(status="passed", label="Đạt", count=passed, pct=pass_rate),
                PassFailBucket(status="failed", label="Chưa đạt", count=failed, pct=round(failed / len(finished) * 100, 1)),
            ]

    # Improvement rate: latest semester GPA improves by at least 0.3 vs previous GPA.
    enrollments_by_student: dict[UUID, dict[str, list[Enrollment]]] = {}
    for e in enrollments:
        enrollments_by_student.setdefault(e.student_id, {}).setdefault(e.semester, []).append(e)
    improved = 0
    comparable = 0
    for semester_map in enrollments_by_student.values():
        sems = sorted(semester_map)
        if len(sems) < 2:
            continue
        prev_sem, current_sem = sems[-2], sems[-1]
        prev_gpa = _semester_gpa_from_enrollments(semester_map[prev_sem])
        current_gpa = _semester_gpa_from_enrollments(semester_map[current_sem])
        if prev_gpa is None or current_gpa is None:
            continue
        comparable += 1
        if current_gpa - prev_gpa >= 0.3:
            improved += 1
    improvement_rate = round(improved / comparable * 100, 1) if comparable else None

    return AdminStatistics(
        gpa_average=round(gpa_avg, 2),
        warning_rate_pct=round(warning_rate, 1),
        improvement_rate_pct=improvement_rate,
        pass_rate_pct=pass_rate,
        total_students=total,
        total_warned=warned,
        total_high_risk=total_high_risk,
        total_critical=total_critical,
        by_semester=by_semester,
        gpa_distribution=distribution,
        by_warning_level=by_warning_level,
        risk_distribution=risk_distribution,
        by_faculty=by_faculty,
        latest_pass_fail=latest_pass_fail,
        semester_now=latest_sem,
    )


def _semester_gpa_from_enrollments(enrollments: list[Enrollment]) -> Optional[float]:
    gpa_enrollments = [
        e for e in enrollments
        if e.course and e.course.credits > 0 and enrollment_gpa_point(e) is not None
    ]
    if not gpa_enrollments:
        return None
    grades = [
        EnrollmentGrade(
            credits=e.course.credits,
            grade_letter=e.grade_letter,
            total_score=e.total_score,
        )
        for e in gpa_enrollments
    ]
    return calculate_semester_gpa(grades)


# ─── Report export ─────────────────────────────────────────

@router.get("/reports/export")
async def export_report(
    report_type: Literal["warnings", "gpa", "ai"] = Query(...),
    format: Literal["xlsx", "pdf"] = Query(...),
    db: AsyncSession = Depends(get_db),
):
    title, columns, rows = await _report_table(db, report_type)
    generated_at = datetime.now(timezone.utc)
    stem = f"{report_type}_report_{generated_at.strftime('%Y%m%d_%H%M%S')}"

    if format == "xlsx":
        data = _build_xlsx_report(title, columns, rows, generated_at)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{stem}.xlsx"'},
        )

    data = _build_pdf_report(title, columns, rows, generated_at)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{stem}.pdf"'},
    )


async def _report_table(
    db: AsyncSession,
    report_type: Literal["warnings", "gpa", "ai"],
) -> tuple[str, list[str], list[list[object]]]:
    if report_type == "warnings":
        rows = (await db.execute(
            select(Warning, Student)
            .join(Student, Warning.student_id == Student.id)
            .order_by(Warning.created_at.desc())
        )).all()
        return (
            "Bao cao canh bao hoc vu",
            ["MSSV", "Ho ten", "Khoa", "Hoc ky", "Muc", "GPA luc canh bao", "Trang thai", "Nguon", "Ngay gui", "Ly do"],
            [
                [
                    s.mssv,
                    s.full_name,
                    s.faculty,
                    w.semester,
                    w.level,
                    round(w.gpa_at_warning or 0.0, 2),
                    "Da xu ly" if w.is_resolved else "Chua xu ly",
                    w.created_by.value,
                    _format_report_datetime(w.sent_at or w.created_at),
                    w.reason,
                ]
                for w, s in rows
            ],
        )

    students = (await db.execute(select(Student).order_by(Student.mssv))).scalars().all()
    if report_type == "gpa":
        return (
            "Bao cao GPA sinh vien",
            ["MSSV", "Ho ten", "Khoa", "Nganh", "Khoa hoc", "GPA tich luy", "Tin chi dat", "Muc canh bao"],
            [
                [
                    s.mssv,
                    s.full_name,
                    s.faculty,
                    s.major,
                    s.cohort,
                    round(s.gpa_cumulative or 0.0, 2),
                    s.credits_earned,
                    s.warning_level,
                ]
                for s in students
            ],
        )

    preds = await _latest_predictions_map(db, [s.id for s in students])
    return (
        "Bao cao du bao AI",
        ["MSSV", "Ho ten", "Khoa", "GPA", "Muc canh bao", "Risk score", "Risk level", "Hoc ky du bao", "Ngay du bao"],
        [
            [
                s.mssv,
                s.full_name,
                s.faculty,
                round(s.gpa_cumulative or 0.0, 2),
                s.warning_level,
                round(p.risk_score, 4) if (p := preds.get(s.id)) else "",
                p.risk_level.value if p else "Chua du bao",
                p.semester if p else "",
                _format_report_datetime(p.created_at) if p else "",
            ]
            for s in students
        ],
    )


def _format_report_datetime(value: Optional[datetime]) -> str:
    if not value:
        return ""
    return value.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")


def _build_xlsx_report(
    title: str,
    columns: list[str],
    rows: list[list[object]],
    generated_at: datetime,
) -> bytes:
    import zipfile

    last_row = max(5, len(rows) + 4)
    last_col = max(1, len(columns))
    rows_xml = [
        _xlsx_row(1, [(1, title, 2)]),
        _xlsx_row(2, [(1, f"Generated at: {_format_report_datetime(generated_at)}", 3)]),
        _xlsx_row(4, [(idx, column, 1) for idx, column in enumerate(columns, start=1)]),
    ]
    for row_idx, row in enumerate(rows, start=5):
        rows_xml.append(
            _xlsx_row(row_idx, [(idx, value, 0) for idx, value in enumerate(row, start=1)])
        )

    col_xml = []
    for col_idx, column in enumerate(columns, start=1):
        sample = [column, *[row[col_idx - 1] for row in rows[:200]]]
        width = min(max(len(str(value)) for value in sample) + 2, 48)
        col_xml.append(f'<col min="{col_idx}" max="{col_idx}" width="{width}" customWidth="1"/>')

    last_ref = f"{_xlsx_col(last_col)}{last_row}"
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="A1:{last_ref}"/>'
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="4" topLeftCell="A5" '
        'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
        f'<cols>{"".join(col_xml)}</cols>'
        f'<sheetData>{"".join(rows_xml)}</sheetData>'
        f'<autoFilter ref="A4:{last_ref}"/>'
        '</worksheet>'
    )

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _XLSX_CONTENT_TYPES)
        archive.writestr("_rels/.rels", _XLSX_RELS)
        archive.writestr("xl/workbook.xml", _XLSX_WORKBOOK)
        archive.writestr("xl/_rels/workbook.xml.rels", _XLSX_WORKBOOK_RELS)
        archive.writestr("xl/styles.xml", _XLSX_STYLES)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    output.seek(0)
    return output.read()


_XLSX_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

_XLSX_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

_XLSX_WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""

_XLSX_WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

_XLSX_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="4">
    <font><sz val="11"/><color theme="1"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><color rgb="FF16358F"/><name val="Calibri"/></font>
    <font><b/><sz val="16"/><color rgb="FF16358F"/><name val="Calibri"/></font>
    <font><i/><sz val="11"/><color rgb="FF667085"/><name val="Calibri"/></font>
  </fonts>
  <fills count="3">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFE8EEFC"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border/>
    <border><bottom style="thin"><color rgb="FFB8C4D8"/></bottom></border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="4">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="top" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"><alignment vertical="top" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
    <xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
  </cellXfs>
</styleSheet>"""


def _xlsx_col(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters or "A"


def _xlsx_escape(value: object) -> str:
    from xml.sax.saxutils import escape

    return escape(str(value), {'"': "&quot;"})


def _xlsx_row(row_idx: int, cells: list[tuple[int, object, int]]) -> str:
    cell_xml = []
    for col_idx, value, style in cells:
        ref = f"{_xlsx_col(col_idx)}{row_idx}"
        cell_xml.append(
            f'<c r="{ref}" s="{style}" t="inlineStr"><is><t>{_xlsx_escape(value)}</t></is></c>'
        )
    return f'<row r="{row_idx}">{"".join(cell_xml)}</row>'


def _build_pdf_report(
    title: str,
    columns: list[str],
    rows: list[list[object]],
    generated_at: datetime,
) -> bytes:
    lines = [
        (title, 16),
        (f"Generated at: {_format_report_datetime(generated_at)}", 9),
        (f"Total rows: {len(rows)}", 9),
        ("", 9),
        (" | ".join(columns), 9),
        ("-" * 145, 9),
    ]
    for row in rows[:160]:
        values = [str(value).replace("\n", " ") for value in row]
        lines.append((" | ".join(values), 8))
    if len(rows) > 160:
        lines.extend([
            ("", 9),
            (f"PDF preview shows first 160 rows. Export Excel for full {len(rows)} rows.", 9),
        ])

    pages = [lines[index:index + 52] for index in range(0, len(lines), 52)] or [[("No data", 9)]]
    objects: list[bytes | None] = [
        None,
        None,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    page_ids: list[int] = []
    for page_lines in pages:
        stream = _pdf_content_stream(page_lines)
        content_id = len(objects) + 1
        objects.append(
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )
        page_id = len(objects) + 1
        page_ids.append(page_id)
        objects.append(None)
        objects[page_id - 1] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")
    return _assemble_pdf([obj or b"" for obj in objects])


def _pdf_escape(value: str) -> str:
    safe = value.encode("latin-1", "replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")[:145]


def _pdf_content_stream(lines: list[tuple[str, int]]) -> bytes:
    y = 800
    chunks: list[str] = []
    for text, size in lines:
        if text:
            chunks.append(f"BT /F1 {size} Tf 40 {y} Td ({_pdf_escape(text)}) Tj ET")
        y -= 14
    return "\n".join(chunks).encode("latin-1", "replace")


def _assemble_pdf(objects: list[bytes]) -> bytes:
    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode("ascii"))
        data.extend(obj)
        data.extend(b"\nendobj\n")

    xref_offset = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    data.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
        .encode("ascii")
    )
    return bytes(data)


# ─── Threshold (read-only) ──────────────────────────────────

@router.get("/threshold", response_model=ThresholdConfig)
async def get_threshold():
    return ThresholdConfig(
        ai_early_warning_threshold=settings.AI_EARLY_WARNING_THRESHOLD,
    )
