"""Excel/CSV import service cho admin (M7).

Hỗ trợ 2 luồng:
  1. Import danh sách sinh viên (tạo user + student record)
  2. Import bảng điểm (tạo/cập nhật enrollment, auto-tạo course nếu chưa có)

History được lưu in-memory deque (mất khi restart) — đủ cho demo. Không persist vào DB
để tránh thêm migration ở M7.
"""
from __future__ import annotations

import io
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Iterator

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.course import Course
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.student import Student
from app.models.user import User, UserRole
from app.schemas.admin import ImportError as ImportErrorSchema
from app.schemas.admin import ImportHistoryItem, ImportResult


# ─── Templates definitions ──────────────────────────────────

STUDENT_COLUMNS = ["mssv", "email", "full_name", "faculty", "major", "cohort", "password"]
STUDENT_REQUIRED = ["mssv", "email", "full_name", "faculty", "major", "cohort"]

GRADE_COLUMNS = [
    "mssv", "course_code", "course_name", "credits", "semester",
    "midterm_score", "lab_score", "other_score", "final_score",
    "midterm_weight", "lab_weight", "other_weight", "final_weight",
    "total_score", "grade_letter", "status", "attendance_rate",
]
GRADE_REQUIRED = ["mssv", "course_code", "semester"]


# ─── In-memory history ──────────────────────────────────────

_HISTORY: deque[ImportHistoryItem] = deque(maxlen=50)


def get_history() -> list[ImportHistoryItem]:
    return list(_HISTORY)


def _log(item: ImportHistoryItem) -> None:
    _HISTORY.appendleft(item)


# ─── Helpers ────────────────────────────────────────────────

def _read_excel(content: bytes) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(content), engine="openpyxl", dtype=str)
    df = df.where(pd.notna(df), None)
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _required_cols(df: pd.DataFrame, required: list[str]) -> list[str]:
    return [c for c in required if c not in df.columns]


def _to_int(v: Any, default: int | None = None) -> int | None:
    if v is None or v == "":
        return default
    try:
        return int(float(str(v).strip()))
    except (ValueError, TypeError):
        return default


def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).strip().replace(",", "."))
    except (ValueError, TypeError):
        return None


def _to_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


# ─── Template generators (xlsx bytes) ───────────────────────

def build_students_template() -> bytes:
    df = pd.DataFrame(
        [{
            "mssv": "2211234",
            "email": "minhkhoa@hcmut.edu.vn",
            "full_name": "Nguyễn Minh Khoa",
            "faculty": "Khoa học và Kỹ thuật Máy tính",
            "major": "Khoa học Máy tính",
            "cohort": 2022,
            "password": "password123",
        }],
        columns=STUDENT_COLUMNS,
    )
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="students", index=False)
    return buf.getvalue()


def build_grades_template() -> bytes:
    df = pd.DataFrame(
        [{
            "mssv": "2211234",
            "course_code": "CO1007",
            "course_name": "Cấu trúc rời rạc",
            "credits": 3,
            "semester": "241",
            "midterm_score": 7.5,
            "lab_score": "",
            "other_score": "",
            "final_score": 8.0,
            "midterm_weight": 0.3,
            "lab_weight": 0,
            "other_weight": 0,
            "final_weight": 0.7,
            "total_score": 7.85,
            "grade_letter": "B+",
            "status": "passed",
            "attendance_rate": 95,
        }],
        columns=GRADE_COLUMNS,
    )
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="grades", index=False)
    return buf.getvalue()


def _iter_rows(df: pd.DataFrame) -> Iterator[tuple[int, dict[str, Any]]]:
    for idx, row in df.iterrows():
        yield int(idx) + 2, row.to_dict()  # +2: 1-based + header row


# ─── Import students ────────────────────────────────────────

async def import_students(
    db: AsyncSession,
    *,
    file_bytes: bytes,
    filename: str,
    uploader_email: str | None,
    default_password: str = "password123",
) -> ImportResult:
    errors: list[ImportErrorSchema] = []
    created = updated = skipped = 0

    try:
        df = _read_excel(file_bytes)
    except Exception as e:
        return ImportResult(
            type="students", filename=filename, total_rows=0,
            created=0, updated=0, skipped=0,
            errors=[ImportErrorSchema(row=0, reason=f"Không đọc được file: {e}")],
            success=False,
        )

    missing = _required_cols(df, STUDENT_REQUIRED)
    if missing:
        return ImportResult(
            type="students", filename=filename, total_rows=len(df),
            created=0, updated=0, skipped=0,
            errors=[ImportErrorSchema(row=1, reason=f"Thiếu cột bắt buộc: {', '.join(missing)}")],
            success=False,
        )

    for row_num, row in _iter_rows(df):
        mssv = _to_str(row.get("mssv"))
        email = _to_str(row.get("email"))
        full_name = _to_str(row.get("full_name"))
        faculty = _to_str(row.get("faculty"))
        major = _to_str(row.get("major"))
        cohort = _to_int(row.get("cohort"))
        password = _to_str(row.get("password")) or default_password

        if not all([mssv, email, full_name, faculty, major]):
            errors.append(ImportErrorSchema(
                row=row_num, reason="Thiếu trường bắt buộc (mssv/email/full_name/faculty/major)",
                raw=row,
            ))
            continue
        if cohort is None:
            errors.append(ImportErrorSchema(row=row_num, column="cohort", reason="Cohort không hợp lệ", raw=row))
            continue

        existing = (await db.execute(
            select(Student).where(Student.mssv == mssv)
        )).scalar_one_or_none()

        if existing:
            existing.full_name = full_name
            existing.faculty = faculty
            existing.major = major
            existing.cohort = cohort
            updated += 1
            continue

        existing_user = (await db.execute(
            select(User).where(User.email == email)
        )).scalar_one_or_none()
        if existing_user:
            errors.append(ImportErrorSchema(
                row=row_num, column="email",
                reason=f"Email {email} đã tồn tại với tài khoản khác",
                raw=row,
            ))
            continue

        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.student,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        student = Student(
            id=uuid.uuid4(),
            user_id=user.id,
            mssv=mssv,
            full_name=full_name,
            faculty=faculty,
            major=major,
            cohort=cohort,
        )
        db.add(student)
        created += 1

    if (created + updated) > 0:
        await db.commit()
    else:
        await db.rollback()

    result = ImportResult(
        type="students", filename=filename, total_rows=len(df),
        created=created, updated=updated, skipped=skipped,
        errors=errors, success=len(errors) == 0,
    )
    _log(ImportHistoryItem(
        id=uuid.uuid4(), type="students", filename=filename,
        total_rows=len(df), created=created, updated=updated,
        error_count=len(errors), success=result.success,
        uploaded_at=datetime.now(timezone.utc), uploaded_by_email=uploader_email,
    ))
    return result


# ─── Import grades ──────────────────────────────────────────

_STATUS_MAP = {
    "passed": EnrollmentStatus.passed,
    "p": EnrollmentStatus.passed,
    "đạt": EnrollmentStatus.passed,
    "failed": EnrollmentStatus.failed,
    "f": EnrollmentStatus.failed,
    "không đạt": EnrollmentStatus.failed,
    "withdrawn": EnrollmentStatus.withdrawn,
    "rt": EnrollmentStatus.withdrawn,
    "exempt": EnrollmentStatus.exempt,
    "mt": EnrollmentStatus.exempt,
    "miễn": EnrollmentStatus.exempt,
    "enrolled": EnrollmentStatus.enrolled,
}


def _parse_status(v: Any) -> EnrollmentStatus | None:
    s = _to_str(v)
    if not s:
        return None
    return _STATUS_MAP.get(s.lower())


async def import_grades(
    db: AsyncSession,
    *,
    file_bytes: bytes,
    filename: str,
    uploader_email: str | None,
) -> ImportResult:
    errors: list[ImportErrorSchema] = []
    created = updated = skipped = 0

    try:
        df = _read_excel(file_bytes)
    except Exception as e:
        return ImportResult(
            type="grades", filename=filename, total_rows=0,
            created=0, updated=0, skipped=0,
            errors=[ImportErrorSchema(row=0, reason=f"Không đọc được file: {e}")],
            success=False,
        )

    missing = _required_cols(df, GRADE_REQUIRED)
    if missing:
        return ImportResult(
            type="grades", filename=filename, total_rows=len(df),
            created=0, updated=0, skipped=0,
            errors=[ImportErrorSchema(row=1, reason=f"Thiếu cột bắt buộc: {', '.join(missing)}")],
            success=False,
        )

    student_cache: dict[str, Student] = {}
    course_cache: dict[str, Course] = {}

    for row_num, row in _iter_rows(df):
        mssv = _to_str(row.get("mssv"))
        course_code = _to_str(row.get("course_code"))
        semester = _to_str(row.get("semester"))

        if not (mssv and course_code and semester):
            errors.append(ImportErrorSchema(
                row=row_num, reason="Thiếu mssv / course_code / semester", raw=row,
            ))
            continue

        student = student_cache.get(mssv)
        if student is None:
            student = (await db.execute(
                select(Student).where(Student.mssv == mssv)
            )).scalar_one_or_none()
            if student is None:
                errors.append(ImportErrorSchema(
                    row=row_num, column="mssv",
                    reason=f"Không tìm thấy sinh viên MSSV={mssv}", raw=row,
                ))
                continue
            student_cache[mssv] = student

        course = course_cache.get(course_code)
        if course is None:
            course = (await db.execute(
                select(Course).where(Course.course_code == course_code)
            )).scalar_one_or_none()
            if course is None:
                course_name = _to_str(row.get("course_name"))
                credits = _to_int(row.get("credits"))
                if not course_name or not credits:
                    errors.append(ImportErrorSchema(
                        row=row_num, column="course_code",
                        reason=f"Môn {course_code} chưa có trong hệ thống — cần điền course_name + credits để auto-tạo",
                        raw=row,
                    ))
                    continue
                course = Course(
                    id=uuid.uuid4(),
                    course_code=course_code,
                    name=course_name,
                    credits=credits,
                    faculty=_to_str(row.get("faculty")) or "Khác",
                )
                db.add(course)
                await db.flush()
            course_cache[course_code] = course

        existing = (await db.execute(
            select(Enrollment).where(
                Enrollment.student_id == student.id,
                Enrollment.course_id == course.id,
                Enrollment.semester == semester,
            )
        )).scalar_one_or_none()

        midterm = _to_float(row.get("midterm_score"))
        lab = _to_float(row.get("lab_score"))
        other = _to_float(row.get("other_score"))
        final = _to_float(row.get("final_score"))
        midterm_w = _to_float(row.get("midterm_weight"))
        lab_w = _to_float(row.get("lab_weight"))
        other_w = _to_float(row.get("other_weight"))
        final_w = _to_float(row.get("final_weight"))
        total = _to_float(row.get("total_score"))
        grade_letter = _to_str(row.get("grade_letter"))
        status = _parse_status(row.get("status"))
        attendance = _to_float(row.get("attendance_rate"))

        if existing:
            if midterm is not None: existing.midterm_score = midterm
            if lab is not None: existing.lab_score = lab
            if other is not None: existing.other_score = other
            if final is not None: existing.final_score = final
            if midterm_w is not None: existing.midterm_weight = midterm_w
            if lab_w is not None: existing.lab_weight = lab_w
            if other_w is not None: existing.other_weight = other_w
            if final_w is not None: existing.final_weight = final_w
            if total is not None: existing.total_score = total
            if grade_letter: existing.grade_letter = grade_letter
            if status: existing.status = status
            if attendance is not None: existing.attendance_rate = attendance
            existing.source = "admin_import"
            if total is not None and grade_letter:
                existing.is_finalized = True
            updated += 1
        else:
            enrollment = Enrollment(
                id=uuid.uuid4(),
                student_id=student.id,
                course_id=course.id,
                semester=semester,
                midterm_score=midterm,
                lab_score=lab,
                other_score=other,
                final_score=final,
                midterm_weight=midterm_w if midterm_w is not None else 0.3,
                lab_weight=lab_w if lab_w is not None else 0.0,
                other_weight=other_w if other_w is not None else 0.0,
                final_weight=final_w if final_w is not None else 0.7,
                total_score=total,
                grade_letter=grade_letter,
                status=status or EnrollmentStatus.enrolled,
                attendance_rate=attendance,
                is_finalized=bool(total is not None and grade_letter),
                source="admin_import",
            )
            db.add(enrollment)
            created += 1

    if (created + updated) > 0:
        await db.commit()

    result = ImportResult(
        type="grades", filename=filename, total_rows=len(df),
        created=created, updated=updated, skipped=skipped,
        errors=errors, success=len(errors) == 0,
    )
    _log(ImportHistoryItem(
        id=uuid.uuid4(), type="grades", filename=filename,
        total_rows=len(df), created=created, updated=updated,
        error_count=len(errors), success=result.success,
        uploaded_at=datetime.now(timezone.utc), uploaded_by_email=uploader_email,
    ))
    return result
