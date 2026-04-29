"""
GPA Calculator — Quy chế đào tạo HCMUT.

Thang điểm:
  9.0–10  → A+ → 4.0
  8.5–8.9 → A  → 4.0
  8.0–8.4 → B+ → 3.5
  7.0–7.9 → B  → 3.0
  6.5–6.9 → C+ → 2.5
  5.5–6.4 → C  → 2.0
  5.0–5.4 → D+ → 1.5
  4.0–4.9 → D  → 1.0
  < 4.0   → F  → 0.0

Điểm chữ đặc biệt (từ myBK, không tính GPA):
  RT  — Rút môn (withdrawn)
  MT  — Miễn điểm (exempt), tính TC nhưng không tính GPA
  DT  — Điểm đạt không có điểm số, tính TC nhưng không tính GPA
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ─── Bảng quy đổi ────────────────────────────────────────────

_SCALE: list[tuple[float, str, float]] = [
    (9.0, "A+", 4.0),
    (8.5, "A",  4.0),
    (8.0, "B+", 3.5),
    (7.0, "B",  3.0),
    (6.5, "C+", 2.5),
    (5.5, "C",  2.0),
    (5.0, "D+", 1.5),
    (4.0, "D",  1.0),
    (0.0, "F",  0.0),
]

# Điểm chữ đặc biệt không có điểm số tương ứng
_SPECIAL_LETTERS = {"RT", "MT", "DT", "CT", "VT", "CH", "KD", "VP", "HT"}

# Điểm chữ không tính vào GPA (tính TC nếu là MT/DT)
_NO_GPA_LETTERS = {"RT", "MT", "DT"}


# ─── Chuyển đổi điểm số ──────────────────────────────────────

def score_to_grade_letter(score: float) -> str:
    """Chuyển điểm thang 10 → điểm chữ."""
    for threshold, letter, _ in _SCALE:
        if score >= threshold:
            return letter
    return "F"


def score_to_gpa_point(score: float) -> float:
    """Chuyển điểm thang 10 → điểm GPA thang 4."""
    for threshold, _, gpa in _SCALE:
        if score >= threshold:
            return gpa
    return 0.0


def grade_letter_to_gpa_point(letter: str) -> Optional[float]:
    """
    Chuyển điểm chữ → GPA point.
    Trả None nếu là điểm chữ đặc biệt (không tính GPA).
    """
    if letter in _NO_GPA_LETTERS:
        return None
    for _, l, gpa in _SCALE:
        if l == letter:
            return gpa
    return None


# ─── Tính điểm tổng kết từ thành phần ────────────────────────

def compute_total_score(
    midterm: Optional[float],
    lab: Optional[float],
    other: Optional[float],
    final: Optional[float],
    midterm_weight: float = 0.3,
    lab_weight: float = 0.0,
    other_weight: float = 0.0,
    final_weight: float = 0.7,
) -> Optional[float]:
    """
    Tính điểm tổng kết từ các thành phần.
    Trả None nếu thiếu điểm cho bất kỳ thành phần nào có weight > 0.
    """
    components = [
        (midterm, midterm_weight),
        (lab,     lab_weight),
        (other,   other_weight),
        (final,   final_weight),
    ]
    total = 0.0
    for score, weight in components:
        if weight > 0:
            if score is None:
                return None
            total += score * weight
    return round(total, 2)


# ─── GPA học kỳ / tích lũy ───────────────────────────────────

@dataclass
class EnrollmentGrade:
    """Input đơn giản để tính GPA — dùng nội bộ."""
    credits: int
    grade_letter: Optional[str] = None
    total_score: Optional[float] = None


def calculate_semester_gpa(enrollments: list[EnrollmentGrade]) -> float:
    """
    Tính GPA học kỳ theo công thức: Σ(gpa_point × credits) / Σcredits.
    Bỏ qua các môn RT / MT / DT / điểm đặc biệt khác.
    """
    total_points = 0.0
    total_credits = 0

    for e in enrollments:
        letter = e.grade_letter
        if letter in _SPECIAL_LETTERS:
            continue

        # Lấy gpa_point từ grade_letter nếu có, nếu không thì tính từ total_score
        gpa_point: Optional[float] = None
        if letter:
            gpa_point = grade_letter_to_gpa_point(letter)
        elif e.total_score is not None:
            gpa_point = score_to_gpa_point(e.total_score)

        if gpa_point is None:
            continue

        total_points += gpa_point * e.credits
        total_credits += e.credits

    if total_credits == 0:
        return 0.0
    return round(total_points / total_credits, 2)


def calculate_gpa_trend(semester_gpas: list[float]) -> float:
    """
    Tính xu hướng GPA 3 học kỳ gần nhất (slope tuyến tính).
    Dương = tăng, âm = giảm.
    """
    recent = semester_gpas[-3:] if len(semester_gpas) >= 3 else semester_gpas
    n = len(recent)
    if n < 2:
        return 0.0

    x_mean = (n - 1) / 2
    y_mean = sum(recent) / n

    numerator = sum((i - x_mean) * (recent[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 3)
