"""
Seed 20 deterministic student users from M6 myBK transcript test cases.

Run inside backend container:
    python -m scripts.seed_m6_test_users

Accounts:
    test1@hcmut.edu.vn  ... test20@hcmut.edu.vn
    password: 04072004
"""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select

from app.ai.prediction.model import prediction_service
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.course import Course
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.notification import Notification
from app.models.prediction import Prediction
from app.models.student import Student
from app.models.user import User, UserRole
from app.models.warning import Warning
from app.services.gpa_calculator import EnrollmentGrade, calculate_semester_gpa
from app.services.grade_aggregator import sync_student_stats
from app.services.mybk_parser import ParsedCourse, parse_mybk_text
from app.services.warning_engine import evaluate_and_persist


PASSWORD = "04072004"
TEST_DIR = Path(__file__).resolve().parents[1] / "tests" / "test-data" / "m6-warning-mybk-cases"


def _case_no(path: Path) -> int:
    match = re.match(r"tc(\d+)_", path.name)
    return int(match.group(1)) if match else 999


def _extract_name(raw: str, fallback: str) -> str:
    match = re.search(r"Họ và tên:\s*(.+)", raw)
    return match.group(1).strip() if match else fallback


def _semester_gpa(courses: list[ParsedCourse], semester: str) -> float | None:
    grades = [
        EnrollmentGrade(
            credits=course.credits,
            grade_letter=course.grade_letter,
            total_score=course.total_score,
        )
        for course in courses
        if course.semester == semester
        and course.credits > 0
        and course.grade_letter not in {"RT", "MT", "DT", "CT", "VT", "CH", "KD", "VP", "HT"}
    ]
    if not grades:
        return None
    return calculate_semester_gpa(grades)


async def _upsert_student(db, index: int, raw: str) -> Student:
    email = f"test{index}@hcmut.edu.vn"
    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            hashed_password=hash_password(PASSWORD),
            role=UserRole.student,
            is_active=True,
            email_notifications_enabled=False,
        )
        db.add(user)
        await db.flush()
    else:
        user.hashed_password = hash_password(PASSWORD)
        user.role = UserRole.student
        user.is_active = True
        user.email_notifications_enabled = False

    mssv = f"TEST{index:04d}"
    student = await db.scalar(select(Student).where(Student.mssv == mssv))
    student_for_user = await db.scalar(select(Student).where(Student.user_id == user.id))
    if student is None:
        student = student_for_user
    elif student_for_user is not None and student_for_user.id != student.id:
        await db.delete(student_for_user)
        await db.flush()

    if student is None:
        student = Student(
            user_id=user.id,
            mssv=mssv,
            full_name=_extract_name(raw, f"Sinh viên Test {index:02d}"),
            faculty="Khoa Khoa học và Kỹ thuật Máy tính",
            major="Khoa học Máy tính",
            cohort=2022,
            gpa_cumulative=0.0,
            credits_earned=0,
            warning_level=0,
        )
        db.add(student)
        await db.flush()
    else:
        student.user_id = user.id
        student.mssv = mssv
        student.full_name = _extract_name(raw, f"Sinh viên Test {index:02d}")
        student.faculty = "Khoa Khoa học và Kỹ thuật Máy tính"
        student.major = "Khoa học Máy tính"
        student.cohort = 2022
        student.warning_level = 0

    await db.commit()
    await db.refresh(student)
    return student


async def _clear_student_data(db, student: Student) -> None:
    await db.execute(delete(Warning).where(Warning.student_id == student.id))
    await db.execute(delete(Notification).where(Notification.student_id == student.id))
    await db.execute(delete(Prediction).where(Prediction.student_id == student.id))
    await db.execute(delete(Enrollment).where(Enrollment.student_id == student.id))
    await db.commit()


async def _import_transcript(db, student: Student, raw: str) -> tuple[int, str | None, float | None]:
    transcript = parse_mybk_text(raw)
    if not transcript.courses:
        raise RuntimeError(f"{student.mssv}: transcript has no courses")

    created = 0
    for pc in transcript.courses:
        course = await db.scalar(select(Course).where(Course.course_code == pc.course_code))
        if course is None:
            course = Course(
                course_code=pc.course_code,
                name=pc.name,
                credits=pc.credits,
                faculty="",
            )
            db.add(course)
            await db.flush()
        else:
            course.name = pc.name
            if pc.credits > 0:
                course.credits = pc.credits

        db.add(
            Enrollment(
                student_id=student.id,
                course_id=course.id,
                semester=pc.semester,
                total_score=pc.total_score,
                grade_letter=pc.grade_letter,
                status=EnrollmentStatus(pc.status),
                is_finalized=True,
                source="m6_test_case",
                midterm_weight=0.0,
                lab_weight=0.0,
                other_weight=0.0,
                final_weight=0.0,
            )
        )
        created += 1

    await db.commit()
    await sync_student_stats(student, db)
    await db.refresh(student)

    latest_semester = max(transcript.semesters_found) if transcript.semesters_found else None
    semester_gpa = _semester_gpa(transcript.courses, latest_semester) if latest_semester else None
    if latest_semester:
        await evaluate_and_persist(
            db=db,
            student=student,
            semester=latest_semester,
            semester_gpa=semester_gpa,
        )
    return created, latest_semester, semester_gpa


async def main() -> None:
    files = sorted(TEST_DIR.glob("tc*.txt"), key=_case_no)
    if len(files) < 20:
        raise RuntimeError(f"Expected at least 20 transcript cases, found {len(files)} in {TEST_DIR}")

    if not prediction_service.is_loaded:
        prediction_service.load()

    async with AsyncSessionLocal() as db:
        print("Seeding M6 transcript users...")
        for index, path in enumerate(files[:20], start=1):
            raw = path.read_text(encoding="utf-8")
            student = await _upsert_student(db, index, raw)
            await _clear_student_data(db, student)
            created, latest_semester, semester_gpa = await _import_transcript(db, student, raw)
            if prediction_service.is_loaded:
                await prediction_service.predict_for_student(student, db, save=True)
            await db.refresh(student)
            print(
                f"test{index}@hcmut.edu.vn / {PASSWORD} -> {path.name}: "
                f"{created} courses, GPA={student.gpa_cumulative:.2f}, "
                f"warning={student.warning_level}, latest={latest_semester}, sem_gpa={semester_gpa}"
            )

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
