"""
Tests for warning_engine pure logic (M6.1).

Cover 5+ scenarios theo CLAUDE.md quy chế HCMUT:
- GPA tích lũy < 1.2 → mức 1
- GPA học kỳ < 0.8 → mức 1
- GPA tích lũy < 1.0 → mức 2
- 2 HK liên tiếp mức 1 → mức 2
- GPA tích lũy < 0.8 → mức 3 (buộc thôi học)
- 3 lần cảnh báo bất kỳ → mức 3
- 2 HK liên tiếp mức 2 → mức 3
- GPA tốt → mức 0
- Edge: GPA = 1.20 chính xác (không cảnh báo)
- AI early warning ngưỡng
"""
from app.services.warning_engine import (
    _is_cold_start_warning,
    check_ai_early_warning,
    check_regulation_warning,
    email_subject_for,
    email_template_for,
    warning_title,
)
from app.models.warning import Warning, WarningCreatedBy


# ─── Mức 1 ─────────────────────────────────────────────


def test_level1_low_cumulative_gpa():
    decision = check_regulation_warning(
        cumulative_gpa=1.15,
        semester_gpa=2.0,
        consecutive_level1_count=0,
        consecutive_level2_count=0,
        total_warnings=0,
    )
    assert decision.level == 1
    assert decision.triggered_by == "regulation_gpa_cumulative"
    assert "1.15" in decision.reason


def test_level1_low_semester_gpa_only():
    """GPA tích lũy OK nhưng GPA HK vừa qua < 0.8 → mức 1."""
    decision = check_regulation_warning(
        cumulative_gpa=2.5,
        semester_gpa=0.6,
        consecutive_level1_count=0,
        consecutive_level2_count=0,
        total_warnings=0,
    )
    assert decision.level == 1
    assert decision.triggered_by == "regulation_gpa_semester"


def test_no_warning_when_borderline_safe():
    """GPA tích lũy = 1.20 chính xác KHÔNG kích hoạt mức 1 (rule là <, không phải <=)."""
    decision = check_regulation_warning(
        cumulative_gpa=1.20,
        semester_gpa=0.80,
        consecutive_level1_count=0,
        consecutive_level2_count=0,
        total_warnings=0,
    )
    assert decision.level == 0


# ─── Mức 2 ─────────────────────────────────────────────


def test_level2_low_cumulative_gpa():
    decision = check_regulation_warning(
        cumulative_gpa=0.95,
        semester_gpa=1.5,
        consecutive_level1_count=0,
        consecutive_level2_count=0,
        total_warnings=1,
    )
    assert decision.level == 2


def test_level2_consecutive_level1():
    """2 HK liên tiếp mức 1 → escalate lên mức 2."""
    decision = check_regulation_warning(
        cumulative_gpa=1.5,  # GPA OK, nhưng đã có 2 lần mức 1 liên tiếp
        semester_gpa=1.0,
        consecutive_level1_count=2,
        consecutive_level2_count=0,
        total_warnings=2,
    )
    assert decision.level == 2
    assert decision.triggered_by == "consecutive"


# ─── Mức 3 — Buộc thôi học ────────────────────────────


def test_level3_critical_gpa():
    decision = check_regulation_warning(
        cumulative_gpa=0.5,
        semester_gpa=0.3,
        consecutive_level1_count=0,
        consecutive_level2_count=0,
        total_warnings=0,
    )
    assert decision.level == 3


def test_level3_three_warnings_history():
    """3 cảnh báo lịch sử (bất kỳ mức) → mức 3."""
    decision = check_regulation_warning(
        cumulative_gpa=2.0,  # GPA OK hiện tại
        semester_gpa=2.0,
        consecutive_level1_count=0,
        consecutive_level2_count=0,
        total_warnings=3,
    )
    assert decision.level == 3


def test_level3_two_consecutive_level2():
    decision = check_regulation_warning(
        cumulative_gpa=1.5,  # GPA hơi lên
        semester_gpa=1.5,
        consecutive_level1_count=0,
        consecutive_level2_count=2,
        total_warnings=2,
    )
    assert decision.level == 3
    assert decision.triggered_by == "consecutive"


# ─── Mức 0 — Bình thường ──────────────────────────────


def test_level0_good_student():
    decision = check_regulation_warning(
        cumulative_gpa=3.5,
        semester_gpa=3.7,
        consecutive_level1_count=0,
        consecutive_level2_count=0,
        total_warnings=0,
    )
    assert decision.level == 0
    assert decision.triggered_by == "none"


# ─── Priority — mức cao nhất thắng ────────────────────


def test_priority_level3_beats_level1():
    """SV có cả điều kiện mức 1 (GPA cumul 1.15) và mức 3 (3 warnings history)
    → trả mức 3 (cao hơn)."""
    decision = check_regulation_warning(
        cumulative_gpa=1.15,
        semester_gpa=0.5,
        consecutive_level1_count=0,
        consecutive_level2_count=0,
        total_warnings=3,
    )
    assert decision.level == 3


# ─── AI Early Warning ─────────────────────────────────


def test_ai_early_warning_above_threshold():
    assert check_ai_early_warning(risk_score=0.65, threshold=0.6) is True


def test_ai_early_warning_below_threshold():
    assert check_ai_early_warning(risk_score=0.55, threshold=0.6) is False


def test_ai_early_warning_none_score():
    assert check_ai_early_warning(risk_score=None) is False


def test_ai_early_warning_at_exact_threshold():
    """0.6 == threshold → True (rule là >=, không phải >)."""
    assert check_ai_early_warning(risk_score=0.6, threshold=0.6) is True


# ─── Helper text ──────────────────────────────────────


def test_warning_title_levels():
    assert "mức 1" in warning_title(1)
    assert "mức 2" in warning_title(2)
    assert "thôi học" in warning_title(3).lower()


def test_email_subject_levels():
    assert "1" in email_subject_for(1)
    assert "khẩn cấp" in email_subject_for(3).lower()


def test_email_template_levels():
    assert email_template_for(1) == "warning_level_1"
    assert email_template_for(2) == "warning_level_2"
    assert email_template_for(3) == "warning_level_3"


# ─── Cold-start cleanup guard ─────────────────────────


def test_detects_cold_start_gpa_zero_warning():
    warning = Warning(
        level=3,
        semester="241",
        reason="GPA tích lũy 0.00 < 0.80 — buộc thôi học theo quy chế HCMUT.",
        gpa_at_warning=0.0,
        ai_risk_score=None,
        created_by=WarningCreatedBy.system,
    )

    assert _is_cold_start_warning(warning) is True


def test_does_not_treat_admin_or_real_gpa_warning_as_cold_start():
    admin_warning = Warning(
        level=3,
        semester="241",
        reason="GPA tích lũy 0.00 < 0.80 — buộc thôi học theo quy chế HCMUT.",
        gpa_at_warning=0.0,
        ai_risk_score=None,
        created_by=WarningCreatedBy.admin,
    )
    real_low_gpa_warning = Warning(
        level=3,
        semester="251",
        reason="GPA tích lũy 0.75 < 0.80 — buộc thôi học theo quy chế HCMUT.",
        gpa_at_warning=0.75,
        ai_risk_score=None,
        created_by=WarningCreatedBy.system,
    )

    assert _is_cold_start_warning(admin_warning) is False
    assert _is_cold_start_warning(real_low_gpa_warning) is False
