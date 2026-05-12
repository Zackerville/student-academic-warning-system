"""Parser for myBK exam schedule (Lịch Kiểm tra - Thi Học kỳ).

Each row has 11 columns:

    Học kỳ | Môn học | Nhóm lớp | Ngày thi | Loại thi | Cơ sở |
    Mã phòng | Thứ | Giờ bắt đầu | Tổng số phút | Cập nhật cuối cùng

Notes:
- Môn học format: "CODE - NAME" e.g. "IM3047 - Giao tiếp trong Kinh doanh"
- Loại thi: "CK" (cuối kỳ) | "GK"/"Ktr" (giữa kỳ)
- Giờ bắt đầu format: "07g00" → "07:00", "09g30" → "09:30"
- Ngày thi format: ISO "2026-05-25"
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ExamEntry:
    course_code: str
    course_name: str
    group: str
    exam_date: str       # ISO date "2026-05-25"
    exam_type: str       # "CK" | "GK"
    campus: str
    room: str
    day_of_week: int | None
    start_time: str      # "07:00"
    duration_min: int

    def to_dict(self) -> dict:
        return {
            "course_code": self.course_code,
            "course_name": self.course_name,
            "group": self.group,
            "exam_date": self.exam_date,
            "exam_type": self.exam_type,
            "campus": self.campus,
            "room": self.room,
            "day_of_week": self.day_of_week,
            "start_time": self.start_time,
            "duration_min": self.duration_min,
        }


@dataclass
class ParsedExamSchedule:
    semester: str
    exams: list[ExamEntry]

    def to_dict(self) -> dict:
        return {
            "semester": self.semester,
            "exams": [e.to_dict() for e in self.exams],
        }


_HEADERS = ("Học kỳ", "Môn học", "Nhóm lớp", "Ngày thi", "Loại thi")
_NOISE = ("Trình bày", "Tổng số", "Copyright", "Version", "Lùi", "Cập nhật cuối")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_COURSE_RE = re.compile(r"^([A-Z]{2,4}\d{3,5})\s*[-–]\s*(.+)$")


def _parse_time(raw: str) -> str:
    """'07g00' → '07:00'; '09g30' → '09:30'. Pass through if already HH:MM."""
    raw = raw.strip().lower().replace("g", ":")
    m = re.match(r"^(\d{1,2}):(\d{2})$", raw)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return raw


def _normalize_type(raw: str) -> str:
    """Map various exam type labels to canonical form."""
    r = raw.strip().upper()
    if r in {"CK", "CUỐI KỲ", "FINAL"}:
        return "CK"
    if r in {"GK", "KTR", "GIỮA KỲ", "MID"}:
        return "GK"
    return r or "GK"


def _semester_from_mybk(raw: str) -> str:
    raw = raw.strip()
    if len(raw) == 5 and raw.isdigit():
        return raw[2:]
    return raw


# Regex anchors: course code prefix, group ending in _Thi/_Ktr, ISO date,
# exam type (CK/GK), campus BK-CS<n>, day 2-8, time HH(g|:)MM, duration digits.
_EXAM_ROW_RE = re.compile(
    r"""
    ^(?P<sem>\d{5,6})\s+
    (?P<code>[A-Z]{2,4}\d{3,5})\s*[-–]\s*
    (?P<name>.+?)\s+
    (?P<group>\w+_(?:Thi|Ktr))\s+
    (?P<date>\d{4}-\d{2}-\d{2})\s+
    (?P<type>CK|GK|Ktr)\s+
    (?P<campus>BK-CS\d)\s+
    (?P<room>\S+)\s+
    (?P<day>\d|-{1,2})\s+
    (?P<time>\d{1,2}[g:]\d{2})\s+
    (?P<dur>\d+)
    (?:\s+\S+\s+\S+)?\s*$       # optional "last updated" timestamp
    """,
    re.VERBOSE,
)


def _split_row_tab(line: str) -> list[str]:
    """Fast path for clean tab-separated input."""
    return [c.strip() for c in line.split("\t")]


def _reconstruct_blob(paste_text: str) -> str:
    """Drop noise/header lines and join the rest into one blob.

    Like TKB, exam rows can wrap across line breaks when copied from the
    web page directly. Joining gives us a single string we can split on
    semester boundaries.
    """
    kept: list[str] = []
    for line in paste_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if any(h in line for h in _HEADERS) and not _DATE_RE.search(line):
            continue
        if any(n in line for n in _NOISE):
            continue
        kept.append(line)
    return " ".join(kept)


def _split_rows(blob: str) -> list[str]:
    """Split on each 5-digit semester boundary followed by a course code."""
    parts = re.split(r"(?:^|(?<=\s))(?=\d{5}\s+[A-Z]{2,4}\d{3,5}\b)", blob)
    return [p.strip() for p in parts if p.strip()]


def parse_exam_schedule(paste_text: str) -> ParsedExamSchedule:
    exams: list[ExamEntry] = []
    semester: str | None = None

    # Path A: clean tab-separated input — use column-based parsing per line.
    if "\t" in paste_text:
        for line in paste_text.splitlines():
            if not line.strip():
                continue
            if any(h in line for h in _HEADERS) and not _DATE_RE.search(line):
                continue
            if any(n in line for n in _NOISE):
                continue
            cells = _split_row_tab(line)
            if len(cells) < 10:
                continue
            sem_raw = cells[0]
            if not (sem_raw.isdigit() and 3 <= len(sem_raw) <= 6):
                continue
            try:
                course_raw = cells[1].strip()
                m = _COURSE_RE.match(course_raw)
                if m:
                    course_code = m.group(1)
                    course_name = m.group(2).strip()
                else:
                    parts = course_raw.split(" - ", 1)
                    if len(parts) != 2:
                        continue
                    course_code, course_name = parts[0].strip(), parts[1].strip()

                group = cells[2].strip()
                exam_date = cells[3].strip()
                if not _DATE_RE.match(exam_date):
                    continue
                exam_type_raw = cells[4].strip()
                if "Ktr" in group and exam_type_raw.upper() == "GK":
                    exam_type = "GK"
                else:
                    exam_type = _normalize_type(exam_type_raw)
                campus = cells[5].strip()
                room = cells[6].strip()
                day_raw = cells[7].strip()
                day = int(day_raw) if day_raw.isdigit() and 2 <= int(day_raw) <= 8 else None
                start_time = _parse_time(cells[8])
                duration = int(cells[9]) if cells[9].strip().isdigit() else 0
                if semester is None:
                    semester = _semester_from_mybk(sem_raw)
                exams.append(
                    ExamEntry(
                        course_code=course_code, course_name=course_name, group=group,
                        exam_date=exam_date, exam_type=exam_type, campus=campus,
                        room=room, day_of_week=day, start_time=start_time,
                        duration_min=duration,
                    )
                )
            except (ValueError, IndexError):
                continue

    # Path B: wrapped web-page paste — single-space rows. Use regex.
    if not exams:
        blob = _reconstruct_blob(paste_text)
        for row in _split_rows(blob):
            m = _EXAM_ROW_RE.match(row)
            if not m:
                continue
            try:
                day_raw = m.group("day")
                day = int(day_raw) if day_raw.isdigit() and 2 <= int(day_raw) <= 8 else None
                exam_type = _normalize_type(m.group("type"))
                if semester is None:
                    semester = _semester_from_mybk(m.group("sem"))
                exams.append(
                    ExamEntry(
                        course_code=m.group("code"),
                        course_name=m.group("name").strip(),
                        group=m.group("group"),
                        exam_date=m.group("date"),
                        exam_type=exam_type,
                        campus=m.group("campus"),
                        room=m.group("room"),
                        day_of_week=day,
                        start_time=_parse_time(m.group("time")),
                        duration_min=int(m.group("dur")),
                    )
                )
            except (ValueError, IndexError):
                continue

    if not exams:
        raise ValueError(
            "Không tìm thấy lịch thi nào hợp lệ. Copy toàn bộ bảng từ myBK "
            "(Lịch kiểm tra - Thi Học kỳ) gồm các cột: Học kỳ, Môn học, Nhóm "
            "lớp, Ngày thi, Loại thi, Cơ sở, Mã phòng, Thứ, Giờ bắt đầu, ..."
        )

    return ParsedExamSchedule(semester=semester or "", exams=exams)
