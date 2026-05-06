"""
Recommender Engine — rule-based gợi ý theo tình trạng SV (M6.2).

Pure functions (không chạm DB), nhận data đã enrich vào, trả dataclass.
Caller (study_plan.py service) load data + ghép pieces lại.

Quy tắc credit_load (theo CLAUDE.md HCMUT regime):
- Cảnh báo mức 3 hoặc GPA < 1.0     → 12-14 TC, ưu tiên hồi phục
- Cảnh báo mức 2 hoặc GPA < 1.5     → 14-17 TC
- Cảnh báo mức 1 hoặc GPA < 2.0     → 15-19 TC
- GPA 2.0-3.0                        → 17-21 TC (chuẩn full-time)
- GPA >= 3.0                         → 18-25 TC (cho phép load nặng)

Quy tắc retake_priority:
- F còn hiệu lực + môn nhiều TC → priority 1
- F còn hiệu lực + môn ít TC    → priority 2
- D đã passed nhưng GPA < 2.0   → priority 3 (cải thiện)
- D+ trở lên + đã passed        → không gợi ý
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class CreditLoad:
    min_credits: int
    recommended_credits: int
    max_credits: int
    rationale: str


@dataclass
class RetakeSuggestion:
    course_id: UUID
    course_code: str
    course_name: str
    credits: int
    last_grade_letter: Optional[str]
    last_total_score: Optional[float]
    last_semester: str
    reason: str
    priority: int


def recommend_credit_load(
    *,
    gpa_cumulative: float,
    warning_level: int,
) -> CreditLoad:
    """Quyết định khoảng tín chỉ phù hợp với tình trạng học vụ hiện tại."""
    if warning_level >= 3:
        return CreditLoad(
            min_credits=10,
            recommended_credits=12,
            max_credits=14,
            rationale=(
                "Bạn đang ở diện buộc thôi học. Khuyến nghị giảm tải tối đa, "
                "ưu tiên học lại các môn đã rớt và phối hợp với cố vấn học tập / Phòng Đào tạo."
            ),
        )
    if warning_level == 2 or gpa_cumulative < 1.0:
        return CreditLoad(
            min_credits=12,
            recommended_credits=14,
            max_credits=17,
            rationale=(
                "Bạn đang cảnh báo mức 2 hoặc GPA tích lũy rất thấp. "
                "Nên chọn 12-17 TC, dồn lực học lại các môn F để kéo GPA và tránh leo lên buộc thôi học."
            ),
        )
    if warning_level == 1 or gpa_cumulative < 1.5:
        return CreditLoad(
            min_credits=14,
            recommended_credits=16,
            max_credits=19,
            rationale=(
                "Bạn đang cảnh báo mức 1 hoặc GPA dưới mức an toàn. "
                "Nên giữ 14-19 TC, ưu tiên môn F học lại trước khi đăng ký môn mới."
            ),
        )
    if gpa_cumulative < 2.0:
        return CreditLoad(
            min_credits=15,
            recommended_credits=18,
            max_credits=21,
            rationale=(
                "GPA dưới 2.0 — bạn có thể học bình thường nhưng nên tránh load nặng "
                "và chọn các môn có khả năng đạt B/B+ để kéo GPA dần lên."
            ),
        )
    if gpa_cumulative < 3.0:
        return CreditLoad(
            min_credits=15,
            recommended_credits=18,
            max_credits=21,
            rationale=(
                "GPA của bạn ở mức trung bình ổn. Có thể đăng ký 15-21 TC tùy lịch cá nhân; "
                "ưu tiên các môn có nhiều TC và phù hợp tiến độ chương trình."
            ),
        )
    return CreditLoad(
        min_credits=18,
        recommended_credits=21,
        max_credits=25,
        rationale=(
            "GPA của bạn cao — đủ điều kiện đăng ký tới 25 TC nếu cần. "
            "Có thể chọn thêm môn tự chọn / nâng cao để tận dụng học kỳ."
        ),
    )


def recommend_retake_priority(
    *,
    unresolved_failed: list[dict],
    low_grade_passed: list[dict],
) -> list[RetakeSuggestion]:
    """
    Sắp xếp danh sách môn nên học lại theo priority.

    Args:
        unresolved_failed: list[{course_id, code, name, credits, last_score, last_letter, semester}]
            — môn đang failed (effective enrollment).
        low_grade_passed: tương tự nhưng cho môn đã passed nhưng điểm thấp (D, D+).
    """
    suggestions: list[RetakeSuggestion] = []

    for item in unresolved_failed:
        credits = int(item.get("credits") or 0)
        priority = 1 if credits >= 3 else 2
        reason = "Môn còn chưa đạt — cần học lại để qua môn và kéo GPA"
        suggestions.append(
            RetakeSuggestion(
                course_id=item["course_id"],
                course_code=item["course_code"],
                course_name=item["course_name"],
                credits=credits,
                last_grade_letter=item.get("last_grade_letter"),
                last_total_score=item.get("last_total_score"),
                last_semester=item.get("last_semester", ""),
                reason=reason,
                priority=priority,
            )
        )

    for item in low_grade_passed:
        credits = int(item.get("credits") or 0)
        suggestions.append(
            RetakeSuggestion(
                course_id=item["course_id"],
                course_code=item["course_code"],
                course_name=item["course_name"],
                credits=credits,
                last_grade_letter=item.get("last_grade_letter"),
                last_total_score=item.get("last_total_score"),
                last_semester=item.get("last_semester", ""),
                reason="Điểm thấp — học cải thiện có thể kéo GPA lên (HCMUT giữ điểm cao nhất)",
                priority=3,
            )
        )

    suggestions.sort(key=lambda s: (s.priority, -s.credits))
    return suggestions
