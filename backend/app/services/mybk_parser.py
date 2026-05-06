"""
myBK Paste Parser — xử lý Ctrl+A → Ctrl+C từ trang Bảng điểm myBK.

Format thực tế (tab-separated từ table HTML):
  Semester header:  "Năm học 2025 - 2026 / Học kỳ 1\t2.4\t110\tTích lũy chung"
  Course row:       "1\tCO4029\tĐồ án Chuyên ngành\t17\tRT\t2\t\tKhông in...\tCN05\t..."
                     [stt] [code] [name]              [score] [grade] [tc]

Điểm đặc biệt: RT, MT, DT, CT, VT, CH, KD, VP, HT — không tính GPA.
Score > 10 là mã nội bộ myBK (e.g. 17, 21, 12) → bỏ qua.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ─── Constants ───────────────────────────────────────────────

_GRADE_LETTERS = {
    "A+", "A", "B+", "B", "C+", "C", "D+", "D", "F",
    "RT", "MT", "DT", "CT", "VT", "CH", "KD", "VP", "HT",
}
_NO_SCORE_LETTERS  = {"RT", "MT", "DT", "CT", "VT", "CH", "KD", "VP", "HT"}
_WITHDRAWN_LETTERS = {"RT"}
_EXEMPT_LETTERS    = {"MT"}
_FAIL_LETTERS      = {"F"}
_PASS_LETTERS      = {"A+", "A", "B+", "B", "C+", "C", "D+", "D", "DT"}

# Semester header: "Năm học 2025 - 2026 / Học kỳ 1"
_SEMESTER_RE = re.compile(
    r"n[aă]m\s+h[oọ]c\s+(\d{4})\s*[-–—]\s*\d{4}\s*/\s*h[oọ]c\s+k[yỳ]\s+(\d+)",
    re.IGNORECASE,
)

# Fallback: "Học kỳ 1 năm học 2021-2022" (old-style plain text)
_SEMESTER_RE_OLD = re.compile(
    r"h[oọ]c\s+k[yỳ]\s+(\d)\s+n[aă]m\s+h[oọ]c\s+(\d{4})[–\-]\d{4}",
    re.IGNORECASE,
)

# Fallback: "HK 241"
_SEMESTER_RE_CODE = re.compile(r"\bHK\s*(\d{3})\b", re.IGNORECASE)

# Course code: CO4029, SP1037, JPN_GC, CCGDTC, PE1047, SA0002 ...
_CODE_RE = re.compile(r"^[A-Z]{1,6}[\d_]{0,5}[A-Z0-9]*$")


# ─── Data classes ────────────────────────────────────────────

@dataclass
class ParsedCourse:
    semester: str
    course_code: str
    name: str
    credits: int
    total_score: Optional[float]
    grade_letter: Optional[str]
    status: str  # enrolled | passed | failed | withdrawn | exempt


@dataclass
class ParsedTranscript:
    courses: list[ParsedCourse] = field(default_factory=list)
    semesters_found: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)


# ─── Helpers ─────────────────────────────────────────────────

def _semester_code(year_start: int, hk: int) -> str:
    return f"{str(year_start)[2:]}{hk}"


def _detect_semester(line: str) -> Optional[str]:
    # "Năm học 2025 - 2026 / Học kỳ 1"
    m = _SEMESTER_RE.search(line)
    if m:
        return _semester_code(int(m.group(1)), int(m.group(2)))
    # "Học kỳ 1 năm học 2021-2022"
    m = _SEMESTER_RE_OLD.search(line)
    if m:
        return _semester_code(int(m.group(2)), int(m.group(1)))
    # "HK 241"
    m = _SEMESTER_RE_CODE.search(line)
    if m:
        return m.group(1)
    return None


def _status_from_letter(letter: str) -> str:
    if letter in _WITHDRAWN_LETTERS:
        return "withdrawn"
    if letter in _EXEMPT_LETTERS:
        return "exempt"
    if letter in _FAIL_LETTERS:
        return "failed"
    if letter in _PASS_LETTERS:
        return "passed"
    return "enrolled"


def _safe_float(s: str) -> Optional[float]:
    try:
        v = float(s.replace(",", "."))
        if 0.0 <= v <= 10.0:
            return round(v, 2)
    except ValueError:
        pass
    return None


def _safe_int(s: str) -> Optional[int]:
    try:
        return int(s.strip())
    except ValueError:
        return None


# ─── Tab-based parser (myBK Ctrl+A format) ───────────────────

def _parse_tabbed_line(line: str, semester: str) -> Optional[ParsedCourse]:
    """
    Tab-separated myBK row:
      col0=stt  col1=code  col2=name  col3=score  col4=grade  col5=credits  col6+= ignored
    """
    parts = line.split("\t")
    if len(parts) < 6:
        return None

    # col0 phải là số thứ tự
    if not re.match(r"^\d+$", parts[0].strip()):
        return None

    course_code = parts[1].strip().upper()
    if not course_code or not _CODE_RE.match(course_code):
        return None

    course_name = parts[2].strip()
    if not course_name:
        return None

    raw_score  = parts[3].strip()
    grade_raw  = parts[4].strip().upper()
    credits_s  = parts[5].strip()

    grade_letter = grade_raw if grade_raw in _GRADE_LETTERS else None

    credits = _safe_int(credits_s) or 0

    total_score: Optional[float] = None
    if grade_letter not in _NO_SCORE_LETTERS:
        total_score = _safe_float(raw_score)   # bỏ qua nếu > 10 (mã nội bộ)

    status = _status_from_letter(grade_letter) if grade_letter else "enrolled"

    return ParsedCourse(
        semester=semester,
        course_code=course_code,
        name=course_name,
        credits=credits,
        total_score=total_score,
        grade_letter=grade_letter,
        status=status,
    )


# ─── Space-based fallback parser ─────────────────────────────

_STATUS_WORDS = {"đạt", "không", "rút", "môn", "miễn", "thi", "điểm", "đặc", "biệt"}


def _parse_spaced_line(line: str, semester: str) -> Optional[ParsedCourse]:
    """Fallback: plain-text dạng 'CO1007  Tên môn  3  8.5  A  Đạt'."""
    tokens = line.split()
    if len(tokens) < 3:
        return None

    code = tokens[0].upper()
    if not _CODE_RE.match(code):
        return None

    rest = list(tokens[1:])

    # Strip trailing status words
    while rest and rest[-1].lower() in _STATUS_WORDS:
        rest.pop()

    # Find grade letter right-to-left
    grade_letter: Optional[str] = None
    for i in range(len(rest) - 1, -1, -1):
        if rest[i].upper() in _GRADE_LETTERS:
            grade_letter = rest.pop(i).upper()
            break

    if grade_letter is None:
        return None

    # Find score right-to-left
    total_score: Optional[float] = None
    if grade_letter not in _NO_SCORE_LETTERS:
        for i in range(len(rest) - 1, -1, -1):
            s = _safe_float(rest[i])
            if s is not None:
                total_score = s
                rest.pop(i)
                break

    # Find credits right-to-left (int 1-10)
    credits: Optional[int] = None
    for i in range(len(rest) - 1, -1, -1):
        tok = rest[i]
        if re.match(r"^\d+$", tok) and 1 <= int(tok) <= 10:
            credits = int(tok)
            rest.pop(i)
            break

    if credits is None:
        return None

    name = " ".join(rest).strip()
    if not name:
        return None

    return ParsedCourse(
        semester=semester,
        course_code=code,
        name=name,
        credits=credits,
        total_score=total_score,
        grade_letter=grade_letter,
        status=_status_from_letter(grade_letter),
    )


# ─── Public API ──────────────────────────────────────────────

def parse_mybk_text(raw: str) -> ParsedTranscript:
    """Parse raw clipboard text từ myBK (Ctrl+A → Ctrl+C)."""
    result = ParsedTranscript()
    current_semester: Optional[str] = None

    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Detect semester header
        sem = _detect_semester(line)
        if sem:
            current_semester = sem
            if sem not in result.semesters_found:
                result.semesters_found.append(sem)
            continue

        if current_semester is None:
            continue

        # Try tab-based first (myBK Ctrl+A), fallback to space-based
        course = _parse_tabbed_line(line, current_semester)
        if course is None:
            course = _parse_spaced_line(line, current_semester)

        if course:
            result.courses.append(course)

    return result
