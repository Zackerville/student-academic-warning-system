"""
Generate tc11-tc20 myBK-style transcripts for M6 warning coverage.

Run from backend container or repo root:
    python backend/scripts/generate_m6_extra_cases.py
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "backend" / "tests" / "test-data" / "m6-warning-mybk-cases"


@dataclass(frozen=True)
class CourseSpec:
    code: str
    name: str
    credits: int
    group: str


SEMESTERS: list[tuple[str, str, int, list[CourseSpec]]] = [
    ("251", "Năm học 2025 - 2026 / Học kỳ 1", 1, [
        CourseSpec("CO4029", "Đồ án Chuyên ngành", 2, "CN05"),
        CourseSpec("SP1037", "Tư tưởng Hồ Chí Minh", 2, "CN01"),
        CourseSpec("CO3029", "Khai phá Dữ liệu", 3, "L03"),
        CourseSpec("CO3117", "Học máy", 3, "CN01"),
        CourseSpec("CO3049", "Lập trình Web", 3, "CN01"),
        CourseSpec("IM1025", "Quản lý Dự án cho Kỹ sư", 3, "CN01"),
    ]),
    ("243", "Năm học 2024 - 2025 / Học kỳ 3", 7, [
        CourseSpec("CO2003", "Cấu trúc Dữ liệu và Giải Thuật", 4, "DT01"),
        CourseSpec("CO3005", "Nguyên lý Ngôn ngữ Lập trình", 4, "DT02"),
        CourseSpec("MT1007", "Đại số Tuyến tính", 3, "DT02"),
        CourseSpec("SP1035", "Chủ nghĩa Xã hội Khoa học", 2, "DT03"),
    ]),
    ("242", "Năm học 2024 - 2025 / Học kỳ 2", 11, [
        CourseSpec("CO3335", "Thực tập Ngoài trường", 2, "CN34"),
        CourseSpec("CO3107", "Thực tập Đồ án môn học Đa ngành - Hướng Trí tuệ Nhân tạo", 1, "CN03"),
        CourseSpec("CO1007", "Cấu trúc Rời rạc cho Khoa học Máy tính", 4, "CN01"),
        CourseSpec("CO1027", "Kỹ thuật Lập trình", 3, "CN01"),
        CourseSpec("SP1039", "Lịch sử Đảng Cộng sản Việt Nam", 2, "CN01"),
        CourseSpec("CO2001", "Kỹ năng Chuyên nghiệp cho Kỹ sư", 3, "CN01"),
    ]),
    ("241", "Năm học 2024 - 2025 / Học kỳ 1", 17, [
        CourseSpec("CO2013", "Hệ cơ sở Dữ liệu", 4, "CN01"),
        CourseSpec("CO2039", "Lập trình Nâng cao", 3, "CN02"),
        CourseSpec("CO2007", "Kiến trúc Máy tính", 4, "CN02"),
        CourseSpec("CO3001", "Công nghệ Phần mềm", 3, "CN01"),
        CourseSpec("CO3093", "Mạng máy tính", 3, "CN01"),
        CourseSpec("CO3085", "Xử lý Ngôn ngữ Tự nhiên", 3, "CN01"),
    ]),
    ("233", "Năm học 2023 - 2024 / Học kỳ 3", 23, [
        CourseSpec("CH1003", "Hóa đại cương", 3, "DTN1"),
        CourseSpec("MT1003", "Giải tích 1", 4, "DT02"),
        CourseSpec("PH1007", "Thí nghiệm Vật lý", 1, "CN04"),
        CourseSpec("LA2019", "Tiếng Nhật 4", 0, "CN03"),
    ]),
    ("232", "Năm học 2023 - 2024 / Học kỳ 2", 27, [
        CourseSpec("MT2013", "Xác suất và Thống kê", 4, "CN01"),
        CourseSpec("SP1033", "Kinh tế Chính trị Mác - Lênin", 2, "CN01"),
        CourseSpec("CO2039", "Lập trình Nâng cao", 3, "CN02"),
        CourseSpec("IM1021", "Khởi nghiệp", 3, "CN01"),
        CourseSpec("CO2017", "Hệ điều hành", 3, "CN01"),
    ]),
    ("231", "Năm học 2023 - 2024 / Học kỳ 1", 32, [
        CourseSpec("CO2003", "Cấu trúc Dữ liệu và Giải Thuật", 4, "CN01"),
        CourseSpec("CO2007", "Kiến trúc Máy tính", 4, "CN02"),
        CourseSpec("SP1031", "Triết học Mác - Lênin", 3, "CN01"),
        CourseSpec("CO2011", "Mô hình hóa Toán học", 3, "CN01"),
        CourseSpec("LA2017", "Tiếng Nhật 3", 0, "CN03"),
    ]),
    ("222", "Năm học 2022 - 2023 / Học kỳ 2", 37, [
        CourseSpec("CO1007", "Cấu trúc Rời rạc cho Khoa học Máy tính", 4, "CN01"),
        CourseSpec("CO1027", "Kỹ thuật Lập trình", 3, "CN01"),
        CourseSpec("PH1007", "Thí nghiệm Vật lý", 1, "CN04"),
        CourseSpec("MT1007", "Đại số Tuyến tính", 3, "CN01"),
        CourseSpec("MT1005", "Giải tích 2", 4, "CN01"),
        CourseSpec("LA1047", "Tiếng Nhật 2", 0, "CN01"),
    ]),
    ("221", "Năm học 2022 - 2023 / Học kỳ 1", 43, [
        CourseSpec("CO1005", "Nhập môn Điện toán", 3, "CN01"),
        CourseSpec("CO1023", "Hệ thống số", 3, "CN01"),
        CourseSpec("PH1003", "Vật lý 1", 4, "CN01"),
        CourseSpec("SP1041", "Kỹ năng mềm", 0, "CN02"),
        CourseSpec("MT1003", "Giải tích 1", 4, "CN01"),
        CourseSpec("LA1045", "Tiếng Nhật 1", 0, "CN01"),
    ]),
]

SCORE_BY_GRADE = {
    "A+": 9.5, "A": 8.8, "B+": 8.2, "B": 7.4, "C+": 6.8,
    "C": 6.0, "D+": 5.2, "D": 4.5, "F": 2.0,
    "RT": 17, "MT": 12, "DT": 21, "CT": 16, "VT": 15, "CH": 11,
    "KD": 18, "VP": 19, "HT": 20,
}
GPA_BY_GRADE = {"A+": 4.0, "A": 4.0, "B+": 3.5, "B": 3.0, "C+": 2.5, "C": 2.0, "D+": 1.5, "D": 1.0, "F": 0.0}

PROFILES = {
    "excellent": ["A+", "A", "A", "B+", "A", "B+"],
    "good": ["B+", "B", "B", "C+", "B+", "B"],
    "medium": ["C+", "C", "B", "D+", "C+", "C"],
    "low": ["D", "D+", "D", "C", "D+", "D"],
    "very_low": ["F", "D", "F", "D", "F", "D+"],
    "all_f": ["F", "F", "F", "F", "F", "F"],
    "all_ch": ["CH", "CH", "CH", "CH", "CH", "CH"],
    "special": ["MT", "DT", "RT", "CH", "VP", "HT"],
}

CASES: list[tuple[int, str, str, dict[str, str], dict[str, dict[str, str]]]] = [
    (11, "tc11_current_semester_pending_no_gpa.txt", "HK 251 toàn CH, lịch sử tốt; không được coi GPA HK là 0.", {
        "251": "all_ch", "243": "good", "242": "good", "241": "good", "233": "medium", "232": "good", "231": "medium", "222": "good", "221": "good",
    }, {}),
    (12, "tc12_transfer_exempt_credit_heavy.txt", "Nhiều MT/DT/RT xen kẽ, chỉ môn có GPA thật mới được tính.", {
        "251": "special", "243": "good", "242": "special", "241": "medium", "233": "special", "232": "good", "231": "medium", "222": "special", "221": "good",
    }, {}),
    (13, "tc13_retake_multiple_courses_recovered.txt", "Nhiều môn F cũ đã học lại đạt, highest-wins phải phục hồi GPA.", {
        "251": "good", "243": "good", "242": "excellent", "241": "medium", "233": "medium", "232": "medium", "231": "all_f", "222": "all_f", "221": "medium",
    }, {"242": {"CO1007": "A", "CO1027": "B+"}, "243": {"CO2003": "B+"}, "232": {"CO2039": "B"}}),
    (14, "tc14_many_unresolved_failed_courses.txt", "GPA tích lũy chưa quá thấp nhưng còn nhiều F chưa xử lý.", {
        "251": "very_low", "243": "good", "242": "very_low", "241": "good", "233": "medium", "232": "good", "231": "medium", "222": "good", "221": "good",
    }, {}),
    (15, "tc15_low_gpa_no_failed_courses_watch_zone.txt", "Toàn D/D+ nhưng không F; sát ngưỡng cảnh báo để test AI watch zone.", {
        "251": "low", "243": "low", "242": "low", "241": "low", "233": "low", "232": "low", "231": "low", "222": "low", "221": "low",
    }, {}),
    (16, "tc16_latest_semester_below_08_safe_cumulative.txt", "GPA tích lũy cao nhưng HK 251 dưới 0.8; phải cảnh báo mức 1 theo GPA HK.", {
        "251": "all_f", "243": "excellent", "242": "excellent", "241": "excellent", "233": "good", "232": "excellent", "231": "good", "222": "excellent", "221": "good",
    }, {}),
    (17, "tc17_long_low_history_level2_level3_path.txt", "Lịch sử dài GPA thấp để test leo mức theo nhiều lần cảnh báo.", {
        "251": "very_low", "243": "low", "242": "very_low", "241": "low", "233": "very_low", "232": "low", "231": "very_low", "222": "low", "221": "very_low",
    }, {}),
    (18, "tc18_partial_effective_data_many_ch_old_terms.txt", "Nhiều học kỳ cũ CH/HT, chỉ vài học kỳ có điểm thật; không cold-start.", {
        "251": "medium", "243": "all_ch", "242": "good", "241": "all_ch", "233": "all_ch", "232": "medium", "231": "all_ch", "222": "all_ch", "221": "all_ch",
    }, {"251": {"CO3049": "F"}, "242": {"CO1027": "B+"}}),
    (19, "tc19_withdraw_then_pass_later.txt", "RT/F cũ sau đó học lại pass; RT không làm hỏng GPA hiệu lực.", {
        "251": "good", "243": "medium", "242": "good", "241": "medium", "233": "medium", "232": "good", "231": "special", "222": "very_low", "221": "medium",
    }, {"231": {"CO2003": "RT", "CO2007": "RT"}, "242": {"CO1007": "B", "CO1027": "B+"}, "243": {"CO2003": "A"}}),
    (20, "tc20_excellent_with_current_pending.txt", "Sinh viên rất tốt nhưng HK hiện tại chưa có điểm; risk phải thấp.", {
        "251": "all_ch", "243": "excellent", "242": "excellent", "241": "excellent", "233": "excellent", "232": "excellent", "231": "excellent", "222": "excellent", "221": "excellent",
    }, {}),
]


def grade_for(profile: str, index: int) -> str:
    grades = PROFILES[profile]
    return grades[index % len(grades)]


def semester_gpa(courses: list[CourseSpec], grades: list[str]) -> float:
    pts = 0.0
    credits = 0
    for course, grade in zip(courses, grades):
        if course.credits <= 0 or grade not in GPA_BY_GRADE:
            continue
        pts += GPA_BY_GRADE[grade] * course.credits
        credits += course.credits
    return round(pts / credits, 2) if credits else 0.0


def render_case(case_no: int, description: str, profiles: dict[str, str], overrides: dict[str, dict[str, str]]) -> str:
    student_name = f"SINH VIEN TEST {case_no:02d}"
    mssv = f"TC20{case_no:04d}"
    lines = [
        "myBk/app",
        "Toggle navigation",
        f"User Image{student_name}",
        "User Image",
        student_name,
        "",
        " Khoa Khoa học và Kỹ thuật Máy tính",
        "Sinh viên",
        "Dịch vụ sinh viên",
        "Kết quả học tập",
        "Hệ thống quản lý Tra thông tin",
        " Tra thông tin Kết quả học tập",
        "Bảng điểm môn học",
        "BẢNG ĐIỂM",
        "Năm học 2025 - 2026 / Học kỳ 1",
        "",
        f"Họ và tên: {student_name}",
        "",
        f"Mã sinh viên: {mssv}",
        "",
        "Mã lớp: CN22KHM7",
        "",
        "Cập nhật cuối: 06/05/2026 05:20",
        "Các điểm đặc biệt: CT = Cấm thi, VT = Vắng thi, CH = Chưa có điểm, RT = Rút môn học, KD = Không đạt, VP = Vắng thi có phép, DT = Điểm đạt, HT = Hoãn thi, MT = Điểm miễn.",
        "",
        "Điểm hệ 4 áp dụng từ khóa 2021.",
        "",
        f"Ghi chú testcase: {description}",
        "",
        "Bảng điểm",
        "Môn học xét tương đương",
        "Danh mục các điểm khác",
        "Stt\tMã môn học\tTên môn học\tĐiểm tổng kết\tTín chỉ\tĐạt\tTình trạng\tNhóm\tGhi chú",
    ]

    stt = 1
    cumulative_gpa = 0.0
    cumulative_credits = 0
    for sem_code, header, start_index, courses in SEMESTERS:
        profile = profiles[sem_code]
        grades = [
            overrides.get(sem_code, {}).get(course.code, grade_for(profile, idx))
            for idx, course in enumerate(courses)
        ]
        sem_gpa = semester_gpa(courses, grades)
        sem_credits = sum(course.credits for course, grade in zip(courses, grades) if course.credits > 0 and grade in GPA_BY_GRADE)
        if sem_credits:
            cumulative_gpa = sem_gpa if cumulative_credits == 0 else round(
                ((cumulative_gpa * cumulative_credits) + (sem_gpa * sem_credits)) / (cumulative_credits + sem_credits),
                2,
            )
            cumulative_credits += sem_credits
        lines.append(f"{header}\t{cumulative_gpa:.2f}\t{cumulative_credits}\tTích lũy chung")
        lines.append(f"{sem_gpa:.2f}\t{sem_credits}\tTích lũy học kỳ")
        for course, grade in zip(courses, grades):
            score = SCORE_BY_GRADE[grade]
            note = "Không tính TCTL & TBTL" if grade in {"RT", "MT", "DT", "CH", "VP", "HT", "CT", "VT"} else ""
            lines.append(
                f"{stt}\t{course.code}\t{course.name}\t{score}\t{grade}\t{course.credits}\t\t\t{course.group}\t{note}"
            )
            stt += 1

    lines.extend([
        "Môn học chuyển điểm/miễn điểm\t6\t",
        f"{stt}\tLA1007\tAnh văn 3\t12\tMT\t2\t\t\tMIEN\t1089/BKDT-04/4/2023",
        f"{stt + 1}\tCCGDTC\tChứng chỉ Giáo Dục Thể Chất\t21\tDT\t0\t\tKhông in trên bảng điểm\t\tKhông tính TCTL & TBTL",
        "Version 2.4.0Copyright © 2026 Academic Affairs Office. All rights reserved.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for case_no, filename, description, profiles, overrides in CASES:
        path = OUT_DIR / filename
        path.write_text(render_case(case_no, description, profiles, overrides), encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
