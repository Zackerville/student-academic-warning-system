"""Parser for myBK TKB (Thời Khóa Biểu) paste format.

myBK exposes the timetable as an HTML table. There are TWO ways students can
copy it:

1. **Table copy (clean)** — tab-separated cells, one row per line.
2. **Web page copy (wrapped)** — single spaces, rows wrap across multiple
   lines because cells are narrow on screen. Footers like "Trình bày từ
   dòng 1 đến 10..." and "Tổng số tín chỉ đăng ký: 20" sneak in.

Each row has 12 columns:

    HỌC KỲ | MÃ MH | TÊN MÔN HỌC | TÍN CHỈ | TC HỌC PHÍ | NHÓM - TỔ |
    THỨ | TIẾT | GIỜ HỌC | PHÒNG | CƠ SỞ | TUẦN HỌC

Notes:
- "--" in THỨ/TIẾT/GIỜ HỌC means course has no fixed schedule (Đồ án, SHSV...)
- TIẾT format: "4 - 6" → start_period=4, end_period=6
- TUẦN HỌC format: "03|04|05|06|--|--|09|10|11|..." → list active week numbers
- Multiple rows can share the same MÃ MH (course meets on multiple days).

Strategy: clean the input → join all into one text blob → split into rows at
each 5-digit semester boundary → regex-parse each row.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass
class TimetableSession:
    """One row in the TKB = one session of a course."""
    course_code: str
    course_name: str
    credits: int
    group: str
    day_of_week: int | None  # 2..7 (CN=8), None if no fixed schedule
    start_period: int | None
    end_period: int | None
    start_time: str | None    # "9:00"
    end_time: str | None      # "11:50"
    room: str
    campus: str
    active_weeks: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "course_code": self.course_code,
            "course_name": self.course_name,
            "credits": self.credits,
            "group": self.group,
            "day_of_week": self.day_of_week,
            "start_period": self.start_period,
            "end_period": self.end_period,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "room": self.room,
            "campus": self.campus,
            "active_weeks": self.active_weeks,
        }


@dataclass
class ParsedTimetable:
    semester: str  # e.g. "252" (HK2 2025-2026)
    sessions: list[TimetableSession]
    week_1_monday: str | None = None  # ISO date of Monday of academic week 1

    def courses(self) -> list[dict]:
        """Distinct courses (deduped by course_code) — used to create enrollments."""
        seen: dict[str, dict] = {}
        for s in self.sessions:
            if s.course_code in seen:
                continue
            seen[s.course_code] = {
                "course_code": s.course_code,
                "course_name": s.course_name,
                "credits": s.credits,
                "group": s.group,
            }
        return list(seen.values())

    def to_dict(self) -> dict:
        return {
            "semester": self.semester,
            "sessions": [s.to_dict() for s in self.sessions],
            "week_1_monday": self.week_1_monday,
        }


# Lines containing these tokens are header/footer noise and get dropped.
_NOISE_PATTERNS = (
    "HỌC KỲ",       # column header
    "MÃ MH",
    "TÊN MÔN HỌC",
    "TÍN CHỈ",
    "TC HỌC PHÍ",
    "NHÓM - TỔ",
    "GIỜ HỌC",
    "TUẦN HỌC",
    "Trình bày",     # pagination text
    "Tổng số tín",   # footer summary
    "Copyright",     # site footer
    "Version",       # site footer
    "Lùi",           # pagination back button (appears as "Lùi12Tới")
)


def _semester_from_mybk(raw: str) -> str:
    """Convert myBK semester code to internal short form.

    Examples:
      "20252" → "252"  (HK2 năm 2025-2026)
      "20241" → "241"  (HK1 năm 2024-2025)
      "20243" → "243"  (HK hè năm 2024-2025)

    Already-short codes like "252" pass through.
    """
    raw = raw.strip()
    if len(raw) == 5 and raw.isdigit():
        return raw[2:]
    return raw


def _parse_weeks(raw: str) -> list[int]:
    """'03|04|05|--|07|' → [3, 4, 5, 7]"""
    out: list[int] = []
    for token in raw.split("|"):
        t = token.strip()
        if t.isdigit():
            out.append(int(t))
    return out


# Row regex — robust to both tab-separated and space-collapsed forms.
# Anchors on the predictable structures: campus = "BK-CS<digit>",
# weeks = pipe-separated tokens. Course name is lazy-matched.
# Group field uses \S+ to tolerate variations like "L01", "A02", "CN07", "L01_LT".
_ROW_RE = re.compile(
    r"""
    ^(?P<sem>\d{5,6})\s+                       # semester (e.g. 20252)
    (?P<code>[A-Z]{2,4}\d{3,5})\s+              # course code (CO3001, SA0002)
    (?P<name>.+?)\s+                            # course name (lazy)
    (?P<tc>\d+)\s+(?P<tchp>\d+)\s+              # credits, tc học phí
    (?P<group>\S+)\s+                           # group (L01, A02, CN07, L01_LT)
    (?P<thu>\d|-{1,2})\s+                       # thứ
    (?P<tiet>(?:\d+\s*-\s*\d+)|-{1,2})\s+       # tiết (e.g. "4 - 6")
    (?P<gio>(?:\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})|-{1,2})\s+  # giờ học
    (?P<room>\S+)\s+                            # phòng
    (?P<campus>BK-CS\d|\S+)\s+                  # cơ sở
    (?P<weeks>(?:\d{1,2}|-{1,2})(?:\s*\|\s*(?:\d{1,2}|-{1,2}))*\s*\|?)\s*$
    """,
    re.VERBOSE,
)


def _parse_day(raw: str) -> int | None:
    raw = raw.strip().upper()
    if not raw or raw == "--" or raw == "-":
        return None
    if raw == "CN":
        return 8
    if raw.isdigit():
        n = int(raw)
        if 2 <= n <= 8:
            return n
    return None


def _parse_periods(raw: str) -> tuple[int | None, int | None]:
    raw = raw.strip()
    if not raw or raw.startswith("-"):
        return None, None
    m = re.match(r"(\d+)\s*[-–—]\s*(\d+)", raw)
    if m:
        return int(m.group(1)), int(m.group(2))
    if raw.isdigit():
        return int(raw), int(raw)
    return None, None


def _parse_time(raw: str) -> tuple[str | None, str | None]:
    raw = raw.strip()
    if not raw or raw.startswith("-"):
        return None, None
    m = re.match(r"(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})", raw)
    if m:
        return m.group(1), m.group(2)
    return None, None


def _clean_input(paste_text: str) -> str:
    """Drop noise lines (headers, pagination, footers) and collapse whitespace.

    Returns one big space-separated text blob ready for row-splitting.

    Special handling:
    - Tokens like room codes can wrap across a line break with a hyphen at
      end of line ("H6-" + "211" should be "H6-211", not "H6- 211").
    - Browsers sometimes emit non-breaking spaces (U+00A0) when copying from
      HTML tables — normalize these to regular spaces.
    """
    # Normalize non-breaking spaces and zero-width chars from HTML copy
    paste_text = paste_text.replace("\xa0", " ").replace("​", "")
    # Collapse "-\n" into "-" so split tokens like "H6-\n211" re-join cleanly.
    paste_text = re.sub(r"-[ \t]*\r?\n[ \t]*", "-", paste_text)

    kept: list[str] = []
    for line in paste_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if any(noise in line for noise in _NOISE_PATTERNS):
            continue
        kept.append(line)
    # Join with spaces — reunites time ranges that wrapped (e.g. "10:00 -\n11:50"
    # has its newline removed above leaving "10:00 -11:50"; or normal cells
    # separated by line break get the expected space between them).
    return " ".join(kept)


def _split_rows(blob: str) -> list[str]:
    """Split the cleaned text into one row per 5-digit semester boundary."""
    # A row starts with a 5-digit code preceded by whitespace or start-of-string.
    # Lookbehind ensures we don't split inside an alphanumeric course code.
    parts = re.split(r"(?:^|(?<=\s))(?=\d{5}\s+[A-Z]{2,4}\d{3,5}\b)", blob)
    return [p.strip() for p in parts if p.strip()]


# Captures the "Tuần: 20 , Thứ Ba, Ngày 12/5/2026" reference line from
# the page header. Used to anchor the academic week numbering onto real dates.
_WEEK_REF_RE = re.compile(
    r"Tuần\s*:\s*(\d{1,2})\s*[,;]\s*[^,;]*[,;]\s*Ngày\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})",
    re.IGNORECASE,
)


def _extract_week_1_monday(paste_text: str) -> str | None:
    """Find 'Tuần: N, ..., Ngày D/M/Y' in the paste header and compute Monday
    of week 1 of the semester.

    Returns ISO date string (e.g. "2025-12-29") or None if not found.
    """
    m = _WEEK_REF_RE.search(paste_text)
    if not m:
        return None
    try:
        week_num = int(m.group(1))
        day = int(m.group(2))
        month = int(m.group(3))
        year = int(m.group(4))
        ref_date = date(year, month, day)
        # Monday of the reference date's week (weekday(): Mon=0)
        monday_of_ref_week = ref_date - timedelta(days=ref_date.weekday())
        # Walk back (week_num - 1) weeks to find week 1's Monday
        week_1 = monday_of_ref_week - timedelta(weeks=week_num - 1)
        return week_1.isoformat()
    except (ValueError, TypeError):
        return None


def parse_tkb(paste_text: str) -> ParsedTimetable:
    """Parse pasted TKB text into structured sessions.

    Accepts both tab-separated table copies and wrapped web-page copies.
    """
    week_1_monday = _extract_week_1_monday(paste_text)
    blob = _clean_input(paste_text)
    rows = _split_rows(blob)

    sessions: list[TimetableSession] = []
    semester: str | None = None

    for row in rows:
        match = _ROW_RE.match(row)
        if not match:
            continue

        try:
            sem_raw = match.group("sem")
            day = _parse_day(match.group("thu"))
            start_p, end_p = _parse_periods(match.group("tiet"))
            start_t, end_t = _parse_time(match.group("gio"))
            credits = int(match.group("tc")) if match.group("tc").isdigit() else 0
            active_weeks = _parse_weeks(match.group("weeks"))

            if semester is None:
                semester = _semester_from_mybk(sem_raw)

            sessions.append(
                TimetableSession(
                    course_code=match.group("code").strip(),
                    course_name=match.group("name").strip(),
                    credits=credits,
                    group=match.group("group").strip(),
                    day_of_week=day,
                    start_period=start_p,
                    end_period=end_p,
                    start_time=start_t,
                    end_time=end_t,
                    room=match.group("room").strip(),
                    campus=match.group("campus").strip(),
                    active_weeks=active_weeks,
                )
            )
        except (ValueError, IndexError):
            continue

    if not sessions:
        # Diagnostic: did we at least see candidate rows?
        candidate_count = len(rows)
        sample = ""
        if rows:
            sample = f"\n\nVí dụ dòng đầu được tìm thấy nhưng không khớp format:\n{rows[0][:200]}..."

        if candidate_count == 0:
            raise ValueError(
                "Không tìm thấy bất kỳ dòng nào có mã học kỳ + mã môn học (vd: '20252 CO3001 ...').\n\n"
                "Có thể bạn chưa copy đúng bảng TKB. Hãy:\n"
                "1. Đăng nhập mybk.hcmut.edu.vn → Sinh viên → Thời khóa biểu Học kỳ\n"
                "2. Cuộn xuống đến BẢNG dữ liệu (sau dòng 'HỌC KỲ | MÃ MH | TÊN MÔN HỌC | ...')\n"
                "3. Bôi đen từ dòng đầu bảng đến hết bảng (KHÔNG cần copy navigation phía trên)\n"
                "4. Ctrl+C → Paste vào ô"
            )
        raise ValueError(
            f"Tìm thấy {candidate_count} dòng có vẻ là môn học nhưng không khớp format chuẩn. "
            "Có thể format myBK đã thay đổi. Vui lòng kiểm tra lại hoặc liên hệ hỗ trợ."
            + sample
        )

    return ParsedTimetable(
        semester=semester or "",
        sessions=sessions,
        week_1_monday=week_1_monday,
    )
