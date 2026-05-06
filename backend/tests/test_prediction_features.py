import uuid

import pytest

from app.ai.prediction.features import FEATURE_NAMES
from app.ai.prediction.explainer import _format_value
from app.ai.prediction.features import extract_features
from app.ai.prediction.model import _apply_early_warning_calibration, risk_score_to_level
from app.api.v1.students import (
    _count_unresolved_failed,
    _effective_enrollments_per_course,
)
from app.models.course import Course
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.prediction import RiskLevel
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


def _student(gpa: float = 2.5, warning_level: int = 0) -> Student:
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
        warning_level=warning_level,
    )


def _feature_row(**overrides: float) -> dict[str, float]:
    features = {name: 0.0 for name in FEATURE_NAMES}
    features.update(overrides)
    return features


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
async def test_zero_credit_f_is_not_counted_as_unresolved_academic_risk():
    zero_credit_course = _course(credits=0)
    enrollments = [
        _enrollment(zero_credit_course, "243", "F", EnrollmentStatus.failed, 0.0),
    ]
    effective = _effective_enrollments_per_course(enrollments)

    features = await extract_features(_student(gpa=3.3), enrollments)

    assert _count_unresolved_failed(effective) == 0
    assert features["unresolved_failed_courses"] == 0.0
    assert features["unresolved_failed_last_semester"] == 0.0
    assert features["pass_rate_deficit"] == 0.0


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


def test_explainer_labels_are_user_friendly():
    labels = [
        _format_value("attendance_risk", 0.0),
        _format_value("gpa_cumulative_deficit", 0.0),
        _format_value("pass_rate_deficit", 0.019),
        _format_value("unknown_feature", 1.0),
    ]

    assert all("_" not in label for label in labels)
    assert all(":" not in label for label in labels)


def test_calibration_keeps_strong_profile_low():
    score, factors, floor = _apply_early_warning_calibration(
        0.05,
        _student(gpa=3.4),
        _feature_row(pass_rate_deficit=0.0),
    )

    assert score == 0.05
    assert floor == 0.0
    assert factors == []
    assert risk_score_to_level(score) == RiskLevel.low


def test_calibration_ignores_stale_warning_level_for_strong_profile():
    score, factors, floor = _apply_early_warning_calibration(
        0.05,
        _student(gpa=3.4, warning_level=3),
        _feature_row(pass_rate_deficit=0.0),
    )

    assert score == 0.05
    assert floor == 0.0
    assert factors == []
    assert risk_score_to_level(score) == RiskLevel.low


def test_calibration_marks_mid_low_gpa_as_medium_watch_zone():
    score, factors, floor = _apply_early_warning_calibration(
        0.04,
        _student(gpa=2.4),
        _feature_row(pass_rate_deficit=0.03),
    )

    assert score >= 0.30
    assert floor >= 0.30
    assert risk_score_to_level(score) == RiskLevel.medium
    assert any("trung bình-thấp" in f["label"] for f in factors)


def test_calibration_raises_average_gpa_with_unresolved_f_and_retake_history():
    score, factors, floor = _apply_early_warning_calibration(
        0.02,
        _student(gpa=2.8),
        _feature_row(
            unresolved_failed_courses=1.0,
            recovered_failed_courses=6.0,
            pass_rate_deficit=0.03,
        ),
    )

    assert score >= 0.30
    assert floor >= 0.30
    assert risk_score_to_level(score) == RiskLevel.medium
    assert any("môn chưa đạt" in f["label"] for f in factors)


def test_calibration_marks_formal_warning_zone_as_critical():
    score, factors, floor = _apply_early_warning_calibration(
        0.20,
        _student(gpa=1.1, warning_level=1),
        _feature_row(unresolved_failed_courses=3.0),
    )

    assert score >= 0.75
    assert floor >= 0.75
    assert risk_score_to_level(score) == RiskLevel.critical
    assert any("cảnh báo học vụ" in f["label"] for f in factors)
