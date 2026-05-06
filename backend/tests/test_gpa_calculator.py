"""Unit tests cho GPA Calculator — thang điểm HCMUT."""

import pytest
from app.services.gpa_calculator import (
    EnrollmentGrade,
    calculate_gpa_trend,
    calculate_semester_gpa,
    compute_total_score,
    grade_letter_to_gpa_point,
    score_to_gpa_point,
    score_to_grade_letter,
)


# ─── score_to_grade_letter ────────────────────────────────────

class TestScoreToGradeLetter:
    def test_a_plus(self):
        assert score_to_grade_letter(9.0) == "A+"
        assert score_to_grade_letter(10.0) == "A+"
        assert score_to_grade_letter(9.5) == "A+"

    def test_a(self):
        assert score_to_grade_letter(8.5) == "A"
        assert score_to_grade_letter(8.9) == "A"

    def test_b_plus(self):
        assert score_to_grade_letter(8.0) == "B+"
        assert score_to_grade_letter(8.4) == "B+"

    def test_b(self):
        assert score_to_grade_letter(7.0) == "B"
        assert score_to_grade_letter(7.9) == "B"

    def test_c_plus(self):
        assert score_to_grade_letter(6.5) == "C+"
        assert score_to_grade_letter(6.9) == "C+"

    def test_c(self):
        assert score_to_grade_letter(5.5) == "C"
        assert score_to_grade_letter(6.4) == "C"

    def test_d_plus(self):
        assert score_to_grade_letter(5.0) == "D+"
        assert score_to_grade_letter(5.4) == "D+"

    def test_d(self):
        assert score_to_grade_letter(4.0) == "D"
        assert score_to_grade_letter(4.9) == "D"

    def test_f(self):
        assert score_to_grade_letter(3.9) == "F"
        assert score_to_grade_letter(0.0) == "F"


# ─── score_to_gpa_point ──────────────────────────────────────

class TestScoreToGpaPoint:
    def test_a_plus_and_a_both_4(self):
        assert score_to_gpa_point(9.5) == 4.0
        assert score_to_gpa_point(8.7) == 4.0

    def test_b_plus(self):
        assert score_to_gpa_point(8.2) == 3.5

    def test_b(self):
        assert score_to_gpa_point(7.5) == 3.0

    def test_c_plus(self):
        assert score_to_gpa_point(6.7) == 2.5

    def test_c(self):
        assert score_to_gpa_point(6.0) == 2.0

    def test_d_plus(self):
        assert score_to_gpa_point(5.2) == 1.5

    def test_d(self):
        assert score_to_gpa_point(4.5) == 1.0

    def test_f(self):
        assert score_to_gpa_point(3.9) == 0.0
        assert score_to_gpa_point(0.0) == 0.0


# ─── grade_letter_to_gpa_point ───────────────────────────────

class TestGradeLetterToGpaPoint:
    def test_normal_letters(self):
        assert grade_letter_to_gpa_point("A+") == 4.0
        assert grade_letter_to_gpa_point("A")  == 4.0
        assert grade_letter_to_gpa_point("B+") == 3.5
        assert grade_letter_to_gpa_point("B")  == 3.0
        assert grade_letter_to_gpa_point("F")  == 0.0

    def test_special_letters_return_none(self):
        assert grade_letter_to_gpa_point("RT") is None
        assert grade_letter_to_gpa_point("MT") is None
        assert grade_letter_to_gpa_point("DT") is None


# ─── compute_total_score ─────────────────────────────────────

class TestComputeTotalScore:
    def test_default_weights_30_70(self):
        result = compute_total_score(midterm=7.0, lab=None, other=None, final=8.0)
        assert result == round(7.0 * 0.3 + 8.0 * 0.7, 2)

    def test_missing_final_returns_none(self):
        result = compute_total_score(midterm=7.0, lab=None, other=None, final=None)
        assert result is None

    def test_missing_lab_when_weight_zero_ok(self):
        result = compute_total_score(
            midterm=7.0, lab=None, other=None, final=8.0,
            midterm_weight=0.3, lab_weight=0.0, other_weight=0.0, final_weight=0.7,
        )
        assert result is not None

    def test_missing_lab_when_weight_nonzero_returns_none(self):
        result = compute_total_score(
            midterm=7.0, lab=None, other=None, final=8.0,
            midterm_weight=0.3, lab_weight=0.2, other_weight=0.0, final_weight=0.5,
        )
        assert result is None

    def test_four_component_weights(self):
        result = compute_total_score(
            midterm=6.0, lab=8.0, other=7.0, final=9.0,
            midterm_weight=0.3, lab_weight=0.2, other_weight=0.1, final_weight=0.4,
        )
        expected = round(6.0*0.3 + 8.0*0.2 + 7.0*0.1 + 9.0*0.4, 2)
        assert result == expected

    def test_project_only(self):
        result = compute_total_score(
            midterm=None, lab=None, other=9.0, final=None,
            midterm_weight=0.0, lab_weight=0.0, other_weight=1.0, final_weight=0.0,
        )
        assert result == 9.0


# ─── calculate_semester_gpa ──────────────────────────────────

class TestCalculateSemesterGpa:
    def test_basic(self):
        enrollments = [
            EnrollmentGrade(credits=3, grade_letter="A"),   # 4.0
            EnrollmentGrade(credits=2, grade_letter="B"),   # 3.0
        ]
        # (4.0*3 + 3.0*2) / 5 = 18/5 = 3.6
        assert calculate_semester_gpa(enrollments) == 3.6

    def test_skip_rt(self):
        enrollments = [
            EnrollmentGrade(credits=3, grade_letter="A"),
            EnrollmentGrade(credits=3, grade_letter="RT"),
        ]
        assert calculate_semester_gpa(enrollments) == 4.0

    def test_skip_mt(self):
        enrollments = [
            EnrollmentGrade(credits=3, grade_letter="B"),
            EnrollmentGrade(credits=3, grade_letter="MT"),
        ]
        assert calculate_semester_gpa(enrollments) == 3.0

    def test_failed_course_counts(self):
        enrollments = [
            EnrollmentGrade(credits=3, grade_letter="A"),
            EnrollmentGrade(credits=3, grade_letter="F"),
        ]
        # (4.0*3 + 0.0*3) / 6 = 2.0
        assert calculate_semester_gpa(enrollments) == 2.0

    def test_empty_returns_zero(self):
        assert calculate_semester_gpa([]) == 0.0

    def test_from_total_score(self):
        enrollments = [
            EnrollmentGrade(credits=3, total_score=8.5),  # A → 4.0
        ]
        assert calculate_semester_gpa(enrollments) == 4.0


# ─── calculate_gpa_trend ─────────────────────────────────────

class TestCalculateGpaTrend:
    def test_increasing(self):
        trend = calculate_gpa_trend([2.0, 2.5, 3.0])
        assert trend > 0

    def test_decreasing(self):
        trend = calculate_gpa_trend([3.5, 3.0, 2.5])
        assert trend < 0

    def test_stable(self):
        trend = calculate_gpa_trend([3.0, 3.0, 3.0])
        assert trend == 0.0

    def test_single_value_returns_zero(self):
        assert calculate_gpa_trend([3.5]) == 0.0

    def test_uses_last_3_semesters(self):
        # 5 HK nhưng chỉ dùng 3 gần nhất [2.0, 2.5, 3.0]
        trend_long = calculate_gpa_trend([3.5, 3.0, 2.0, 2.5, 3.0])
        trend_short = calculate_gpa_trend([2.0, 2.5, 3.0])
        assert trend_long == trend_short
