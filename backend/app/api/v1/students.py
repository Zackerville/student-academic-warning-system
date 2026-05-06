"""
Student API — /api/v1/students
Endpoints: profile, dashboard, grades, enrollments, GPA, myBK import
"""
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_student, get_db
from app.models.course import Course
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.prediction import Prediction
from app.models.student import Student
from app.schemas.course import CourseCreate, CourseResponse
from app.schemas.enrollment import (
    EnrollmentCreate,
    EnrollmentResponse,
    EnrollmentWithCourse,
    GpaHistoryEntry,
    GradeUpdate,
    GradeUpdateOutcome,
)
from app.schemas.student import StudentResponse
from app.services.gpa_calculator import (
    EnrollmentGrade,
    _SPECIAL_LETTERS,
    calculate_gpa_trend,
    calculate_semester_gpa,
    compute_total_score,
    grade_letter_to_gpa_point,
    score_to_gpa_point,
    score_to_grade_letter,
)
from app.services.grade_aggregator import (
    count_unresolved_failed,
    effective_enrollments_per_course,
    enrollment_gpa_point,
    is_credit_bearing,
    sync_student_stats,
)
from app.services.mybk_parser import ParsedCourse, parse_mybk_text
from app.services import warning_engine

router = APIRouter(prefix="/students", tags=["students"])


# ─── Backward-compat aliases (giữ tên cũ trong file để không phải đổi 7 callsites) ──
# Logic thật ở app.services.grade_aggregator — module này là single source of truth.
_enrollment_gpa_point = enrollment_gpa_point
_is_credit_bearing = is_credit_bearing
_count_unresolved_failed = count_unresolved_failed
_effective_enrollments_per_course = effective_enrollments_per_course
_sync_student_stats = sync_student_stats


async def _invalidate_student_predictions(student_id: UUID, db: AsyncSession) -> None:
    """Drop cached predictions after transcript changes."""
    await db.execute(delete(Prediction).where(Prediction.student_id == student_id))
    await db.commit()


async def _semester_gpa_for_student(
    student_id: UUID,
    semester: str,
    db: AsyncSession,
) -> float | None:
    """Return GPA học kỳ nếu HK có môn GPA-bearing; None nếu toàn điểm đặc biệt/chưa có điểm."""
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student_id, Enrollment.semester == semester)
        .options(selectinload(Enrollment.course))
    )
    enrollments = result.scalars().all()
    gpa_enrollments = [
        e for e in enrollments
        if e.course.credits > 0 and _enrollment_gpa_point(e) is not None
    ]
    if not gpa_enrollments:
        return None
    return calculate_semester_gpa(
        [
            EnrollmentGrade(
                credits=e.course.credits,
                grade_letter=e.grade_letter,
                total_score=e.total_score,
            )
            for e in gpa_enrollments
        ]
    )


# ─── Profile ─────────────────────────────────────────────────

@router.get("/me", response_model=StudentResponse)
async def get_my_profile(student: Student = Depends(get_current_student)):
    return student


# ─── Dashboard summary ───────────────────────────────────────

@router.get("/me/dashboard")
async def get_dashboard(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    # Đảm bảo gpa_cumulative + credits_earned trên student record là mới nhất
    await warning_engine.sync_current_warning_level(db, student)
    await db.refresh(student)

    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student.id)
        .options(selectinload(Enrollment.course))
        .order_by(Enrollment.semester.desc())
    )
    enrollments = result.scalars().all()

    semesters = sorted({e.semester for e in enrollments}, reverse=True)
    current_semester = semesters[0] if semesters else None
    current_enrollments = [e for e in enrollments if e.semester == current_semester]

    # Chỉ đếm môn chưa đạt nếu điểm hiệu lực của môn đó vẫn là F.
    # F đã học lại đạt sẽ không còn được tính vào dashboard.
    effective = _effective_enrollments_per_course(enrollments)
    failed_total = _count_unresolved_failed(effective)
    credits_in_progress = sum(
        e.course.credits for e in current_enrollments
        if e.status == EnrollmentStatus.enrolled
    )

    return {
        "student": StudentResponse.model_validate(student),
        "current_semester": current_semester,
        "credits_in_progress": credits_in_progress,
        "failed_courses_total": failed_total,
        "unresolved_failed_courses": failed_total,
        "semesters_count": len(semesters),
    }


# ─── Enrollments / Grades ────────────────────────────────────

@router.get("/me/enrollments", response_model=list[EnrollmentWithCourse])
async def list_enrollments(
    semester: str | None = None,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Enrollment)
        .where(Enrollment.student_id == student.id)
        .options(selectinload(Enrollment.course))
        .order_by(Enrollment.semester.desc())
    )
    if semester:
        q = q.where(Enrollment.semester == semester)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/me/enrollments/manual", status_code=201)
async def create_enrollment_manual(
    payload: dict,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo enrollment thủ công — tự động upsert course theo course_code.
    Body: { course_code, course_name, credits, faculty?, semester,
            midterm_weight, lab_weight, other_weight, final_weight,
            midterm_score?, lab_score?, other_score?, final_score?, attendance_rate? }
    """
    course_code = payload.get("course_code", "").strip().upper()
    course_name = payload.get("course_name", "").strip()
    credits = int(payload.get("credits", 3))
    faculty = payload.get("faculty", "")
    semester = payload.get("semester", "").strip()

    if not course_code or not course_name or not semester:
        raise HTTPException(status_code=422, detail="Thiếu course_code, course_name hoặc semester")

    mw = float(payload.get("midterm_weight", 0.3))
    lw = float(payload.get("lab_weight", 0.0))
    ow = float(payload.get("other_weight", 0.0))
    fw = float(payload.get("final_weight", 0.7))

    # Upsert course
    result = await db.execute(select(Course).where(Course.course_code == course_code))
    course = result.scalar_one_or_none()
    if not course:
        course = Course(course_code=course_code, name=course_name, credits=credits, faculty=faculty)
        db.add(course)
        await db.flush()

    # Check duplicate enrollment
    existing = await db.execute(
        select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.course_id == course.id,
            Enrollment.semester == semester,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Đã đăng ký môn này trong học kỳ này")

    # Parse scores
    def _score(key: str):
        v = payload.get(key)
        return float(v) if v not in (None, "") else None

    midterm = _score("midterm_score")
    lab = _score("lab_score")
    other = _score("other_score")
    final = _score("final_score")

    total = compute_total_score(
        midterm=midterm, lab=lab, other=other, final=final,
        midterm_weight=mw, lab_weight=lw, other_weight=ow, final_weight=fw,
    )
    grade_letter = score_to_grade_letter(total) if total is not None else None
    if total is not None:
        status = EnrollmentStatus.passed if total >= 4.0 else EnrollmentStatus.failed
    else:
        status = EnrollmentStatus.enrolled

    enrollment = Enrollment(
        student_id=student.id,
        course_id=course.id,
        semester=semester,
        midterm_weight=mw, lab_weight=lw, other_weight=ow, final_weight=fw,
        midterm_score=midterm, lab_score=lab, other_score=other, final_score=final,
        attendance_rate=_score("attendance_rate"),
        total_score=total,
        grade_letter=grade_letter,
        status=status,
        source="manual",
        is_finalized=False,
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    await _sync_student_stats(student, db)
    await _invalidate_student_predictions(student.id, db)

    await db.refresh(enrollment, ["course"])
    return EnrollmentWithCourse.model_validate(enrollment)


@router.post("/me/enrollments", response_model=EnrollmentResponse, status_code=201)
async def create_enrollment(
    payload: EnrollmentCreate,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    # Check course exists
    course = await db.get(Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Môn học không tồn tại")

    # Check duplicate
    existing = await db.execute(
        select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.course_id == payload.course_id,
            Enrollment.semester == payload.semester,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Đã đăng ký môn này trong học kỳ này")

    enrollment = Enrollment(
        student_id=student.id,
        course_id=payload.course_id,
        semester=payload.semester,
        midterm_weight=payload.midterm_weight,
        lab_weight=payload.lab_weight,
        other_weight=payload.other_weight,
        final_weight=payload.final_weight,
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    await _invalidate_student_predictions(student.id, db)
    return enrollment


@router.put("/me/enrollments/{enrollment_id}/grades", response_model=GradeUpdateOutcome)
async def update_grades(
    enrollment_id: UUID,
    payload: GradeUpdate,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.id == enrollment_id,
            Enrollment.student_id == student.id,
        )
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Không tìm thấy enrollment")
    if enrollment.is_finalized:
        raise HTTPException(status_code=409, detail="Điểm đã được chốt (finalized), không thể sửa")

    # Apply score/weight updates
    for field in ("midterm_score", "lab_score", "other_score", "final_score", "attendance_rate"):
        v = getattr(payload, field)
        if v is not None:
            setattr(enrollment, field, v)

    for field in ("midterm_weight", "lab_weight", "other_weight", "final_weight"):
        v = getattr(payload, field)
        if v is not None:
            setattr(enrollment, field, v)

    # Recompute total_score and grade_letter
    total = compute_total_score(
        midterm=enrollment.midterm_score,
        lab=enrollment.lab_score,
        other=enrollment.other_score,
        final=enrollment.final_score,
        midterm_weight=enrollment.midterm_weight,
        lab_weight=enrollment.lab_weight,
        other_weight=enrollment.other_weight,
        final_weight=enrollment.final_weight,
    )
    enrollment.total_score = total
    if total is not None:
        enrollment.grade_letter = score_to_grade_letter(total)
        enrollment.status = (
            EnrollmentStatus.passed if total >= 4.0 else EnrollmentStatus.failed
        )

    await db.commit()
    await db.refresh(enrollment)
    await _sync_student_stats(student, db)
    await _invalidate_student_predictions(student.id, db)

    # ─── M6 Step 6.10: auto-trigger warning sau khi update điểm ────
    # Chỉ chạy khi có total_score (môn đã có điểm cuối) — tránh trigger khi SV
    # mới nhập điểm GK chưa có CK.
    outcome_warning_created = False
    outcome_level = None
    outcome_reason = None
    outcome_ai_early = False
    if enrollment.total_score is not None:
        try:
            outcome = await warning_engine.evaluate_and_persist(
                db=db,
                student=student,
                semester=enrollment.semester,
                semester_gpa=None,  # TODO: compute semester GPA nếu cần precision cao
            )
            outcome_warning_created = outcome.created
            if outcome.decision and outcome.decision.level > 0:
                outcome_level = outcome.decision.level
                outcome_reason = outcome.decision.reason
            outcome_ai_early = outcome.ai_early_warning
        except Exception as exc:  # pragma: no cover - không cản trở update grade
            from loguru import logger
            logger.warning(f"[students.update_grades] warning_engine failed: {exc}")

    return GradeUpdateOutcome(
        enrollment=EnrollmentResponse.model_validate(enrollment),
        warning_created=outcome_warning_created,
        warning_level=outcome_level,
        warning_reason=outcome_reason,
        ai_early_warning=outcome_ai_early,
    )


@router.delete("/me/enrollments/{enrollment_id}", status_code=204)
async def delete_enrollment(
    enrollment_id: UUID,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Xoá 1 môn học của SV — cho phép xoá cả môn manual lẫn môn import từ myBK."""
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.id == enrollment_id,
            Enrollment.student_id == student.id,
        )
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Không tìm thấy enrollment")
    await db.delete(enrollment)
    await db.commit()
    await _sync_student_stats(student, db)
    await _invalidate_student_predictions(student.id, db)


@router.delete("/me/enrollments", status_code=200)
async def delete_all_enrollments(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Xoá toàn bộ bảng điểm của SV — dùng khi muốn re-import lại từ myBK."""
    result = await db.execute(
        select(Enrollment).where(Enrollment.student_id == student.id)
    )
    enrollments = result.scalars().all()
    count = len(enrollments)
    for e in enrollments:
        await db.delete(e)
    await db.commit()
    await _sync_student_stats(student, db)
    await _invalidate_student_predictions(student.id, db)
    return {"message": f"Đã xoá {count} môn học", "deleted": count}


# ─── GPA ─────────────────────────────────────────────────────

@router.get("/me/gpa")
async def get_gpa(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    # Sync stats first to ensure values are up-to-date
    await _sync_student_stats(student, db)
    await db.refresh(student)

    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student.id)
        .options(selectinload(Enrollment.course))
    )
    all_enrollments = result.scalars().all()

    semester_map: dict[str, list[EnrollmentGrade]] = {}
    for e in all_enrollments:
        if e.course.credits == 0:
            continue
        if e.grade_letter or e.total_score is not None:
            eg = EnrollmentGrade(
                credits=e.course.credits,
                grade_letter=e.grade_letter,
                total_score=e.total_score,
            )
            semester_map.setdefault(e.semester, []).append(eg)

    semesters_sorted = sorted(semester_map.keys())
    semester_gpas = [calculate_semester_gpa(semester_map[s]) for s in semesters_sorted]

    return {
        "gpa_cumulative": student.gpa_cumulative,
        "credits_earned": student.credits_earned,
        "warning_level": student.warning_level,
        "gpa_trend": calculate_gpa_trend(semester_gpas),
        "semester_gpas": [
            {"semester": s, "gpa": g}
            for s, g in zip(semesters_sorted, semester_gpas)
        ],
    }


@router.get("/me/gpa/history", response_model=list[GpaHistoryEntry])
async def get_gpa_history(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student.id)
        .options(selectinload(Enrollment.course))
    )
    all_enrollments = result.scalars().all()

    semester_map: dict[str, list[Enrollment]] = {}
    for e in all_enrollments:
        semester_map.setdefault(e.semester, []).append(e)

    history = []
    for sem in sorted(semester_map.keys()):
        sem_enrollments = semester_map[sem]
        gpa_enrollments = [e for e in sem_enrollments if e.course.credits > 0]
        if not gpa_enrollments:
            continue
        grades = [
            EnrollmentGrade(
                credits=e.course.credits,
                grade_letter=e.grade_letter,
                total_score=e.total_score,
            )
            for e in gpa_enrollments
        ]
        history.append(
            GpaHistoryEntry(
                semester=sem,
                semester_gpa=calculate_semester_gpa(grades),
                credits_taken=sum(e.course.credits for e in gpa_enrollments),
                courses_count=len(gpa_enrollments),
            )
        )
    return history


# ─── myBK Paste Import ───────────────────────────────────────

@router.post("/me/grades/import-mybk")
async def import_mybk(
    raw_text: str = Body(..., media_type="text/plain"),
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Nhận raw text paste từ myBK, parse thành enrollments.
    - Tự động tạo Course nếu chưa tồn tại (course_code làm key)
    - Tạo hoặc cập nhật Enrollment cho từng môn
    - Đánh dấu is_finalized=true, source="mybk_paste"
    """
    transcript = parse_mybk_text(raw_text)
    if not transcript.courses:
        if not transcript.semesters_found:
            detail = (
                "Không tìm thấy thông tin học kỳ nào trong nội dung. "
                "Hãy đảm bảo bạn đã vào đúng trang 'Bảng điểm' trên myBK "
                "(không phải trang menu) và bảng điểm đã hiển thị đầy đủ trước khi Ctrl+A."
            )
        else:
            sems = ", ".join(transcript.semesters_found)
            detail = (
                f"Tìm thấy header học kỳ ({sems}) nhưng không có môn học nào. "
                "Bạn có thể đang đứng ở trang menu — hãy click vào link 'Bảng điểm' "
                "trên myBK để xem bảng có cột STT / Mã môn / Tên môn / Điểm, "
                "rồi mới Ctrl+A → Ctrl+C."
            )
        raise HTTPException(status_code=422, detail=detail)

    created_count = 0
    updated_count = 0
    skipped_count = 0

    for pc in transcript.courses:
        # Upsert course by course_code
        course_result = await db.execute(
            select(Course).where(Course.course_code == pc.course_code)
        )
        course = course_result.scalar_one_or_none()
        if not course:
            course = Course(
                course_code=pc.course_code,
                name=pc.name,
                credits=pc.credits,
                faculty="",
            )
            db.add(course)
            await db.flush()  # get course.id
        else:
            # Update credits nếu import có credits lớn hơn (fix cho case
            # course được tạo bởi SV khác với credits sai hoặc = 0)
            if pc.credits > 0 and course.credits != pc.credits:
                course.credits = pc.credits

        # Upsert enrollment
        enroll_result = await db.execute(
            select(Enrollment).where(
                Enrollment.student_id == student.id,
                Enrollment.course_id == course.id,
                Enrollment.semester == pc.semester,
            )
        )
        enrollment = enroll_result.scalar_one_or_none()

        if enrollment and enrollment.is_finalized:
            # Already finalized — update total/grade only, keep component scores
            enrollment.total_score = pc.total_score
            enrollment.grade_letter = pc.grade_letter
            enrollment.status = EnrollmentStatus(pc.status)
            updated_count += 1
        elif enrollment:
            # Existing non-finalized — fully update
            enrollment.total_score = pc.total_score
            enrollment.grade_letter = pc.grade_letter
            enrollment.status = EnrollmentStatus(pc.status)
            enrollment.is_finalized = True
            enrollment.source = "mybk_paste"
            updated_count += 1
        else:
            enrollment = Enrollment(
                student_id=student.id,
                course_id=course.id,
                semester=pc.semester,
                total_score=pc.total_score,
                grade_letter=pc.grade_letter,
                status=EnrollmentStatus(pc.status),
                is_finalized=True,
                source="mybk_paste",
                midterm_weight=0.0,
                lab_weight=0.0,
                other_weight=0.0,
                final_weight=0.0,
            )
            db.add(enrollment)
            created_count += 1

    await db.commit()
    await _sync_student_stats(student, db)
    await _invalidate_student_predictions(student.id, db)

    latest_semester = max(transcript.semesters_found) if transcript.semesters_found else None
    if latest_semester:
        semester_gpa = await _semester_gpa_for_student(student.id, latest_semester, db)
        try:
            await warning_engine.evaluate_and_persist(
                db=db,
                student=student,
                semester=latest_semester,
                semester_gpa=semester_gpa,
            )
        except Exception as exc:  # pragma: no cover - import điểm không bị fail vì email/warning
            from loguru import logger
            logger.warning(f"[students.import_mybk] warning_engine failed: {exc}")

    return {
        "message": "Import thành công",
        "semesters": transcript.semesters_found,
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "total_courses": len(transcript.courses),
    }
