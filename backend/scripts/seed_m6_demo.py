"""
Seed one deterministic M6 demo student.

Run inside backend container:
    python -m scripts.seed_m6_demo

Demo login:
    m6.student@demo.local / student123
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.ai.prediction.model import prediction_service
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.course import Course
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.event import Event, EventType, TargetAudience
from app.models.notification import Notification
from app.models.prediction import Prediction
from app.models.student import Student
from app.models.user import User, UserRole
from app.models.warning import Warning
from app.services.grade_aggregator import sync_student_stats
from app.services.warning_engine import evaluate_and_persist


DEMO_EMAIL = "m6.student@demo.local"
DEMO_PASSWORD = "student123"
DEMO_MSSV = "M6DEMO01"
DEMO_FACULTY = "Khoa Điện - Điện tử"
DEMO_COHORT = 2022


COURSES = [
    ("EE3001", "Hệ thống Điều khiển", 3, "Khoa Điện - Điện tử", "251", 3.8, "F", EnrollmentStatus.failed),
    ("EE2001", "Mạch Điện tử", 4, "Khoa Điện - Điện tử", "251", 4.2, "F", EnrollmentStatus.failed),
    ("MT2013", "Xác suất và Thống kê", 4, "Khoa Khoa học Ứng dụng", "251", 5.0, "D", EnrollmentStatus.passed),
    ("SP1037", "Tư tưởng Hồ Chí Minh", 2, "Khoa Lý luận Chính trị", "251", 5.4, "D+", EnrollmentStatus.passed),
    ("CO1003", "Nhập môn về Lập trình", 3, "Khoa Khoa học và Kỹ thuật Máy tính", "242", 6.0, "C", EnrollmentStatus.passed),
    ("PH1005", "Vật lý 2", 4, "Khoa Khoa học Ứng dụng", "241", 3.5, "F", EnrollmentStatus.failed),
]


async def _get_or_create_demo_student(db) -> Student:
    user = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        user = User(
            email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            role=UserRole.student,
            is_active=True,
            email_notifications_enabled=True,
        )
        db.add(user)
        await db.flush()
    else:
        user.hashed_password = hash_password(DEMO_PASSWORD)
        user.role = UserRole.student
        user.is_active = True
        user.email_notifications_enabled = True

    student = await db.scalar(select(Student).where(Student.mssv == DEMO_MSSV))
    if student is None:
        student = Student(
            user_id=user.id,
            mssv=DEMO_MSSV,
            full_name="Sinh viên Demo M6",
            faculty=DEMO_FACULTY,
            major="Kỹ thuật Điều khiển và Tự động hoá",
            cohort=DEMO_COHORT,
            gpa_cumulative=0.0,
            credits_earned=0,
            warning_level=0,
        )
        db.add(student)
        await db.flush()
    else:
        student.user_id = user.id
        student.full_name = "Sinh viên Demo M6"
        student.faculty = DEMO_FACULTY
        student.major = "Kỹ thuật Điều khiển và Tự động hoá"
        student.cohort = DEMO_COHORT
        student.warning_level = 0

    await db.commit()
    await db.refresh(student)
    return student


async def _clear_demo_student_data(db, student: Student) -> None:
    await db.execute(delete(Warning).where(Warning.student_id == student.id))
    await db.execute(delete(Notification).where(Notification.student_id == student.id))
    await db.execute(delete(Prediction).where(Prediction.student_id == student.id))
    await db.execute(delete(Enrollment).where(Enrollment.student_id == student.id))
    await db.commit()


async def _seed_enrollments(db, student: Student) -> None:
    for code, name, credits, faculty, semester, score, letter, status in COURSES:
        course = await db.scalar(select(Course).where(Course.course_code == code))
        if course is None:
            course = Course(course_code=code, name=name, credits=credits, faculty=faculty)
            db.add(course)
            await db.flush()
        else:
            course.name = name
            course.credits = credits
            course.faculty = faculty

        db.add(
            Enrollment(
                student_id=student.id,
                course_id=course.id,
                semester=semester,
                total_score=score,
                grade_letter=letter,
                status=status,
                is_finalized=True,
                source="m6_demo",
                midterm_weight=0.0,
                lab_weight=0.0,
                other_weight=0.0,
                final_weight=0.0,
            )
        )
    await db.commit()


async def _seed_events(db, admin_user: User | None) -> None:
    await db.execute(delete(Event).where(Event.title.like("[M6 Demo]%")))

    now = datetime.now(tz=timezone.utc)
    events = [
        Event(
            title="[M6 Demo] Hạn đăng ký học lại",
            description="Sự kiện toàn trường để kiểm tra trang Sự kiện của sinh viên.",
            event_type=EventType.submission,
            target_audience=TargetAudience.all,
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=2),
            is_mandatory=True,
            created_by=admin_user.id if admin_user else None,
        ),
        Event(
            title="[M6 Demo] Tư vấn học vụ khoa Điện - Điện tử",
            description="Sự kiện chỉ hiện với sinh viên cùng khoa.",
            event_type=EventType.activity,
            target_audience=TargetAudience.faculty_specific,
            target_value=DEMO_FACULTY,
            start_time=now + timedelta(days=3),
            end_time=now + timedelta(days=3, hours=1),
            is_mandatory=False,
            created_by=admin_user.id if admin_user else None,
        ),
        Event(
            title="[M6 Demo] Khảo sát sinh viên khóa 2022",
            description="Sự kiện chỉ hiện với sinh viên cùng khóa.",
            event_type=EventType.evaluation,
            target_audience=TargetAudience.cohort_specific,
            target_value=str(DEMO_COHORT),
            start_time=now + timedelta(days=5),
            end_time=now + timedelta(days=5, hours=1),
            is_mandatory=False,
            created_by=admin_user.id if admin_user else None,
        ),
    ]
    db.add_all(events)
    await db.commit()


async def main() -> None:
    async with AsyncSessionLocal() as db:
        student = await _get_or_create_demo_student(db)
        await _clear_demo_student_data(db, student)
        await _seed_enrollments(db, student)

        await sync_student_stats(student, db)
        await db.refresh(student)

        if not prediction_service.is_loaded:
            prediction_service.load()
        if prediction_service.is_loaded:
            await prediction_service.predict_for_student(student, db, save=True)

        student = await db.scalar(
            select(Student)
            .where(Student.id == student.id)
            .options(selectinload(Student.user))
        )
        await evaluate_and_persist(db=db, student=student, semester="251", semester_gpa=0.9)

        admin_user = await db.scalar(select(User).where(User.email == "admin@hcmut.edu.vn"))
        await _seed_events(db, admin_user)

        refreshed = await db.scalar(
            select(Student)
            .where(Student.id == student.id)
            .options(selectinload(Student.user))
        )
        print("Seed M6 demo done.")
        print(f"Student login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print(f"MSSV: {DEMO_MSSV}")
        print(f"GPA: {refreshed.gpa_cumulative:.2f}, credits: {refreshed.credits_earned}, warning_level: {refreshed.warning_level}")


if __name__ == "__main__":
    asyncio.run(main())
