import uuid

import pytest

from app.ai.prediction.features import extract_features
from app.api.v1.students import _effective_enrollments_per_course
from app.models.course import Course
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.student import Student


def _course(course_id: uuid.UUID | None = None, credits: int = 3) -> Course:
    return Course(
        id=course_id or uuid.uuid4(),
        course_code=f"CO{uuid.uuid4().int % 10000:04d}",
        name="Test Course",
        credits=credits,
        faculty="Test",
    )


def _enrollment(
    course: Course,
    semester: str,
    grade_letter: str,
    status: EnrollmentStatus,
    total_score: float | None = None,
    attendance_rate: float | None = None,
) -> Enrollment:
    enrollment = Enrollment(
        id=uuid.uuid4(),
        student_id=uuid.uuid4(),
        course_id=course.id,
        semester=semester,
        grade_letter=grade_letter,
        total_score=total_score,
        status=status,
        attendance_rate=attendance_rate,
    )
    enrollment.course = course
    return enrollment


def _student(gpa: float = 2.5) -> Student:
    return Student(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        mssv=f"T{uuid.uuid4().int % 100000:05d}",
        full_name="Test Student",
        faculty="Test",
        major="Test",
        cohort=2021,
        gpa_cumulative=gpa,
        credits_earned=0,
        warning_level=0,
    )


def test_effective_enrollment_uses_best_attempt_not_failed_history():
    course = _course()
    failed = _enrollment(course, "231", "F", EnrollmentStatus.failed, 3.0)
    recovered = _enrollment(course, "241", "B", EnrollmentStatus.passed, 7.5)

    effective = _effective_enrollments_per_course([failed, recovered])

    assert effective == [recovered]
    assert sum(1 for e in effective if e.status == EnrollmentStatus.failed) == 0


@pytest.mark.asyncio
async def test_features_do_not_count_recovered_f_as_current_risk():
    course = _course()
    enrollments = [
        _enrollment(course, "231", "F", EnrollmentStatus.failed, 3.0),
        _enrollment(course, "241", "B", EnrollmentStatus.passed, 7.5),
    ]

    features = await extract_features(_student(gpa=3.0), enrollments)

    assert features["unresolved_failed_courses"] == 0.0
    assert features["unresolved_failed_retake_count"] == 0.0
    assert features["recovered_failed_courses"] == 1.0


@pytest.mark.asyncio
async def test_features_count_retake_only_when_course_is_still_failed():
    course = _course()
    enrollments = [
        _enrollment(course, "231", "F", EnrollmentStatus.failed, 3.0),
        _enrollment(course, "241", "F", EnrollmentStatus.failed, 3.5),
    ]

    features = await extract_features(_student(gpa=0.8), enrollments)

    assert features["unresolved_failed_courses"] == 1.0
    assert features["unresolved_failed_retake_count"] == 1.0
    assert features["recovered_failed_courses"] == 0.0


@pytest.mark.asyncio
async def test_attendance_risk_starts_below_safe_threshold_only():
    course = _course()
    safe_attendance = [
        _enrollment(course, "241", "B", EnrollmentStatus.passed, 7.5, attendance_rate=80.0),
    ]
    low_attendance = [
        _enrollment(course, "241", "B", EnrollmentStatus.passed, 7.5, attendance_rate=60.0),
    ]

    assert (await extract_features(_student(), safe_attendance))["attendance_risk"] == 0.0
    assert (await extract_features(_student(), low_attendance))["attendance_risk"] > 0.0
