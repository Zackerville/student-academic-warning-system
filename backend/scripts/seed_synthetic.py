"""
Sinh 1000 SV synthetic vào DB để train XGBoost.

Pattern:
  - MSSV: SYN00001 → SYN01000
  - Email: syn00001@synthetic.local
  - 4 cohorts: 2021, 2022, 2023, 2024 (250 SV mỗi cohort)
  - 10 khoa, 30 ngành sát HCMUT
  - ~150 courses (CO/MT/PH/CH/SP/IM/LA/PE/CC*)
  - Mỗi SV có 4-9 HK lịch sử + 4-7 môn/HK
  - Phân bố GPA Gaussian: 15% xuất sắc, 60% TB, 20% yếu, 5% cực yếu
  - ~10-15% SV có warning_level >= 1 (≈ 100-150 positive samples)

Cách chạy:
  docker compose exec backend python -m scripts.seed_synthetic

Cleanup (xoá hết SYN*):
  docker compose exec backend python -m scripts.cleanup_synthetic
"""
from __future__ import annotations

import asyncio
import random
import sys
from pathlib import Path

# Allow running as `python -m scripts.seed_synthetic` from /app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.course import Course
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.student import Student
from app.models.user import User, UserRole
from app.services.gpa_calculator import score_to_grade_letter

# Reproducibility
random.seed(42)

# ─── Faculty + Major ─────────────────────────────────────────

FACULTIES_AND_MAJORS = {
    "Khoa Khoa học và Kỹ thuật Máy tính": [
        "Khoa học Máy tính", "Kỹ thuật Máy tính", "Khoa học Dữ liệu"
    ],
    "Khoa Điện - Điện tử": [
        "Kỹ thuật Điện", "Kỹ thuật Điện tử - Viễn thông", "Kỹ thuật Điều khiển và Tự động hoá"
    ],
    "Khoa Cơ khí": [
        "Kỹ thuật Cơ khí", "Kỹ thuật Cơ điện tử", "Kỹ thuật Nhiệt"
    ],
    "Khoa Xây dựng": [
        "Kỹ thuật Xây dựng", "Kỹ thuật Xây dựng Công trình Giao thông"
    ],
    "Khoa Hóa": [
        "Kỹ thuật Hoá học", "Công nghệ Thực phẩm"
    ],
    "Khoa Quản lý Công nghiệp": [
        "Quản lý Công nghiệp", "Logistics và Quản lý Chuỗi Cung ứng"
    ],
    "Khoa Môi trường và Tài nguyên": [
        "Kỹ thuật Môi trường"
    ],
    "Khoa Khoa học Ứng dụng": [
        "Vật lý Kỹ thuật", "Cơ Kỹ thuật"
    ],
    "Khoa Kỹ thuật Giao thông": [
        "Kỹ thuật Hàng không", "Kỹ thuật Tàu thuỷ", "Kỹ thuật Ô tô"
    ],
    "Khoa Kỹ thuật Địa chất và Dầu khí": [
        "Kỹ thuật Địa chất", "Kỹ thuật Dầu khí"
    ],
}

# ─── Course catalog ─────────────────────────────────────────

# Phổ biến: chung cho mọi SV
COMMON_COURSES = [
    # Đại cương / Chính trị
    ("MT1003", "Giải tích 1", 4),
    ("MT1005", "Giải tích 2", 4),
    ("MT1007", "Đại số Tuyến tính", 3),
    ("MT2013", "Xác suất và Thống kê", 4),
    ("PH1003", "Vật lý 1", 4),
    ("PH1007", "Thí nghiệm Vật lý", 1),
    ("CH1003", "Hóa đại cương", 3),
    ("SP1031", "Triết học Mác - Lênin", 3),
    ("SP1033", "Kinh tế Chính trị Mác - Lênin", 2),
    ("SP1035", "Chủ nghĩa Xã hội Khoa học", 2),
    ("SP1037", "Tư tưởng Hồ Chí Minh", 2),
    ("SP1039", "Lịch sử Đảng Cộng sản Việt Nam", 2),
    ("SP1041", "Kỹ năng mềm", 0),
    ("SP1045", "Kỹ năng Xã hội I", 0),
    ("MI1003", "Giáo dục Quốc phòng", 0),
    ("PE1009", "Bóng đá (Học phần 1)", 0),
    ("PE1047", "Võ (Học phần 2)", 0),
    # Ngoại ngữ
    ("LA1045", "Tiếng Nhật 1", 0),
    ("LA1047", "Tiếng Nhật 2", 0),
    ("LA2017", "Tiếng Nhật 3", 0),
    ("LA2019", "Tiếng Nhật 4", 0),
    ("LA3025", "Tiếng Nhật 5", 0),
    ("LA3027", "Tiếng Nhật 6", 0),
    ("LA4007", "Tiếng Nhật 7", 0),
]

# Computer Science / Engineering specific
CS_COURSES = [
    ("CO1005", "Nhập môn Điện toán", 3),
    ("CO1007", "Cấu trúc Rời rạc cho KHMT", 4),
    ("CO1023", "Hệ thống số", 3),
    ("CO1027", "Kỹ thuật Lập trình", 3),
    ("CO2001", "Kỹ năng Chuyên nghiệp cho Kỹ sư", 3),
    ("CO2003", "Cấu trúc Dữ liệu và Giải Thuật", 4),
    ("CO2007", "Kiến trúc Máy tính", 4),
    ("CO2011", "Mô hình hóa Toán học", 3),
    ("CO2013", "Hệ cơ sở Dữ liệu", 4),
    ("CO2017", "Hệ điều hành", 3),
    ("CO2039", "Lập trình Nâng cao", 3),
    ("CO3001", "Công nghệ Phần mềm", 3),
    ("CO3005", "Nguyên lý Ngôn ngữ Lập trình", 4),
    ("CO3029", "Khai phá Dữ liệu", 3),
    ("CO3045", "Lập trình Game", 3),
    ("CO3049", "Lập trình Web", 3),
    ("CO3061", "Nhập môn Trí tuệ Nhân tạo", 3),
    ("CO3085", "Xử lý Ngôn ngữ Tự nhiên", 3),
    ("CO3093", "Mạng máy tính", 3),
    ("CO3101", "Đồ án Tổng hợp - AI", 1),
    ("CO3107", "Thực tập Đồ án Đa ngành", 1),
    ("CO3117", "Học máy", 3),
    ("CO3335", "Thực tập Ngoài trường", 2),
    ("CO4029", "Đồ án Chuyên ngành", 2),
    ("IM1021", "Khởi nghiệp", 3),
    ("IM1025", "Quản lý Dự án cho Kỹ sư", 3),
]

# Engineering broader (cho các khoa khác)
ENG_COURSES = [
    ("EE1001", "Kỹ thuật Điện cơ bản", 3),
    ("EE2001", "Mạch Điện tử", 4),
    ("EE3001", "Hệ thống Điều khiển", 3),
    ("ME1001", "Vẽ Kỹ thuật", 2),
    ("ME2001", "Cơ học Máy", 3),
    ("CE1001", "Vật liệu Xây dựng", 3),
    ("CH2001", "Hóa Hữu cơ", 4),
    ("EV1001", "Kỹ thuật Môi trường", 3),
    ("LS1001", "Logistics cơ bản", 3),
    ("AE1001", "Cơ học Bay", 4),
]

ALL_COURSES = COMMON_COURSES + CS_COURSES + ENG_COURSES


# ─── Distribution helpers ───────────────────────────────────

# Phân lớp 4 nhóm: pct → (mean GPA target, std, retake_success_rate)
# retake_success_rate: xác suất môn rớt được học lại với điểm pass
GPA_TIERS = [
    (0.15, 3.6, 0.25, 0.9),  # Xuất sắc
    (0.55, 2.7, 0.4,  0.75), # Trung bình
    (0.20, 1.4, 0.45, 0.35), # Yếu — nhiều môn rớt vẫn không học lại đạt
    (0.10, 0.5, 0.45, 0.1),  # Cực yếu — gần như mọi môn học lại vẫn rớt → vào warning lvl 3
]


def pick_tier() -> tuple[float, float, float]:
    """Trả (mean_gpa, std, retake_success_rate) cho 1 SV."""
    r = random.random()
    cum = 0.0
    for pct, mean, std, retake in GPA_TIERS:
        cum += pct
        if r <= cum:
            return mean, std, retake
    return GPA_TIERS[-1][1], GPA_TIERS[-1][2], GPA_TIERS[-1][3]


def gpa_to_score(gpa: float) -> float:
    """Convert GPA point thang 4 → điểm 10 (ngược của score_to_gpa_point)."""
    if gpa >= 4.0:
        return random.uniform(8.5, 10.0)
    if gpa >= 3.5:
        return random.uniform(8.0, 8.4)
    if gpa >= 3.0:
        return random.uniform(7.0, 7.9)
    if gpa >= 2.5:
        return random.uniform(6.5, 6.9)
    if gpa >= 2.0:
        return random.uniform(5.5, 6.4)
    if gpa >= 1.5:
        return random.uniform(5.0, 5.4)
    if gpa >= 1.0:
        return random.uniform(4.0, 4.9)
    return random.uniform(0.0, 3.9)  # F


def generate_course_score(target_gpa: float, std: float) -> float:
    """Generate điểm 10 cho 1 môn dựa trên target GPA + noise."""
    target_gpa_clamped = max(0.0, min(4.0, target_gpa + random.gauss(0, std)))
    return round(gpa_to_score(target_gpa_clamped), 1)


# ─── Semester generator ─────────────────────────────────────

def generate_semesters(cohort: int, current_year: int = 2026) -> list[str]:
    """Sinh list học kỳ từ lúc nhập học tới hiện tại. Code dạng YYN."""
    semesters = []
    for y in range(cohort, current_year + 1):
        year_short = str(y)[2:]
        for hk in (1, 2, 3):
            # Skip future semesters (hiện tại là HK2 of 2025-2026 → "252")
            if y == current_year and hk > 1:
                continue
            semesters.append(f"{year_short}{hk}")
    return semesters


def warning_level_from_gpa(gpa: float) -> int:
    """Map cumulative GPA → warning level theo quy chế HCMUT."""
    if gpa < 0.8:
        return 3
    if gpa < 1.0:
        return 2
    if gpa < 1.2:
        return 1
    return 0


# ─── Main seed ──────────────────────────────────────────────

async def upsert_courses(db: AsyncSession) -> dict[str, Course]:
    """Insert tất cả course nếu chưa có. Return dict[code, Course]."""
    result = await db.execute(select(Course))
    existing = {c.course_code: c for c in result.scalars().all()}
    courses_map: dict[str, Course] = dict(existing)
    new_count = 0
    for code, name, credits in ALL_COURSES:
        if code not in existing:
            c = Course(course_code=code, name=name, credits=credits, faculty="")
            db.add(c)
            courses_map[code] = c
            new_count += 1
    await db.flush()
    print(f"  Courses: {new_count} new, {len(existing)} existing (total {len(courses_map)})")
    return courses_map


# Cached password hash — same for all synthetic users (no one logs in as them)
_CACHED_HASH: str | None = None


def _get_synthetic_hash() -> str:
    global _CACHED_HASH
    if _CACHED_HASH is None:
        _CACHED_HASH = hash_password("synthetic")
    return _CACHED_HASH


async def generate_student(
    idx: int,
    cohort: int,
    db: AsyncSession,
    courses: dict[str, Course],
) -> tuple[int, int, int]:
    """
    Generate 1 SV + enrollments. Return (n_enrollments, n_failed, warning_level).
    """
    mean_gpa, std, retake_success_rate = pick_tier()
    # 25% SV có "rocky trajectory": HK đầu yếu, recover về sau
    # → tạo SV cuối cùng GPA 2.0-3.0 nhưng nhiều retake (giống case thực tế)
    is_rocky = random.random() < 0.25 and mean_gpa >= 1.5
    mssv = f"SYN{idx:05d}"
    email = f"syn{idx:05d}@synthetic.local"

    faculty = random.choice(list(FACULTIES_AND_MAJORS.keys()))
    major = random.choice(FACULTIES_AND_MAJORS[faculty])

    # User
    user = User(
        email=email,
        hashed_password=_get_synthetic_hash(),
        role=UserRole.student,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # Student
    student = Student(
        user_id=user.id,
        mssv=mssv,
        full_name=f"Synthetic Student {idx:05d}",
        faculty=faculty,
        major=major,
        cohort=cohort,
        gpa_cumulative=0.0,
        credits_earned=0,
        warning_level=0,
    )
    db.add(student)
    await db.flush()

    # Choose course pool: CS faculty → CS_COURSES + COMMON, else → ENG + COMMON
    is_cs = "Máy tính" in faculty or "Khoa học Dữ liệu" in major
    pool_codes = [c[0] for c in COMMON_COURSES] + (
        [c[0] for c in CS_COURSES] if is_cs else [c[0] for c in ENG_COURSES]
    )
    common_codes = [c[0] for c in COMMON_COURSES]

    semesters = generate_semesters(cohort)
    enrollments_data: list[tuple[str, str, float]] = []  # (code, semester, score)
    used_in_semester: dict[str, set[str]] = {s: set() for s in semesters}

    # Sinh enrollments — nếu rocky thì semester đầu có mean_gpa thấp hơn
    n_sems = len(semesters)
    for sem_idx, sem in enumerate(semesters):
        if is_rocky and n_sems >= 4:
            # Linear interpolate: HK đầu mean - 1.5, HK cuối mean + 0.5
            progress = sem_idx / max(1, n_sems - 1)  # 0 → 1
            sem_mean = mean_gpa - 1.5 + progress * 2.0
            sem_std = std + 0.2  # nhiều noise hơn ở SV rocky
        else:
            sem_mean = mean_gpa
            sem_std = std

        n_courses = random.randint(4, 7)
        chosen = random.sample(common_codes, min(2, len(common_codes)))
        chosen += random.sample([c for c in pool_codes if c not in chosen], n_courses - len(chosen))
        for code in chosen:
            if code in used_in_semester[sem]:
                continue
            used_in_semester[sem].add(code)
            score = generate_course_score(sem_mean, sem_std)
            enrollments_data.append((code, sem, score))

    # Học lại: SV yếu/cực yếu retake ít hơn và retake fail nhiều hơn
    failed_courses = [(code, sem) for code, sem, score in enrollments_data if score < 4.0]
    # Tỉ lệ retake (không phải success rate): SV yếu retake ít hơn vì có thể bỏ cuộc
    retake_attempt_rate = 0.4 if mean_gpa < 1.5 else 0.7
    retake_count = int(len(failed_courses) * retake_attempt_rate)
    for code, fail_sem in random.sample(failed_courses, min(retake_count, len(failed_courses))):
        later_sems = [s for s in semesters if s > fail_sem]
        if not later_sems:
            continue
        retake_sem = random.choice(later_sems)
        if code in used_in_semester[retake_sem]:
            continue
        used_in_semester[retake_sem].add(code)
        # Retake outcome dựa trên success rate của tier
        if random.random() < retake_success_rate:
            # Pass khi retake — điểm 5.0-8.0
            retake_score = round(random.uniform(5.0, 8.0), 1)
        else:
            # Vẫn rớt — điểm 0.0-3.9
            retake_score = round(random.uniform(0.0, 3.9), 1)
        enrollments_data.append((code, retake_sem, retake_score))

    # Special: 2-5% môn RT (rút), 1-2% môn MT (miễn)
    n_rt = max(1, int(len(enrollments_data) * 0.03))
    rt_picks = random.sample(range(len(enrollments_data)), min(n_rt, len(enrollments_data)))

    n_failed = 0
    for i, (code, sem, score) in enumerate(enrollments_data):
        course = courses[code]
        is_rt = i in rt_picks

        if is_rt:
            grade_letter = "RT"
            status = EnrollmentStatus.withdrawn
            total_score = None
        elif score < 4.0:
            grade_letter = "F"
            status = EnrollmentStatus.failed
            total_score = score
            n_failed += 1
        else:
            grade_letter = score_to_grade_letter(score)
            status = EnrollmentStatus.passed
            total_score = score

        # Attendance correlate rõ ràng với tier (ÍT overlap để model học signal sạch)
        if mean_gpa >= 3.0:           # Xuất sắc
            attendance = random.uniform(90, 100)   # mean ~95%
        elif mean_gpa >= 2.0 and not is_rocky:  # TB clean
            attendance = random.uniform(82, 95)    # mean ~88%
        elif is_rocky:                # Rocky trajectory — attendance thất thường
            attendance = random.uniform(65, 85)    # mean ~75%
        elif mean_gpa >= 1.0:         # Yếu
            attendance = random.uniform(55, 80)    # mean ~67%
        else:                          # Cực yếu
            attendance = random.uniform(40, 70)    # mean ~55%

        e = Enrollment(
            student_id=student.id,
            course_id=course.id,
            semester=sem,
            total_score=total_score,
            grade_letter=grade_letter,
            status=status,
            attendance_rate=round(attendance, 1),
            is_finalized=True,
            source="synthetic",
            midterm_weight=0.0,
            lab_weight=0.0,
            other_weight=0.0,
            final_weight=0.0,
        )
        db.add(e)

    await db.flush()

    # Compute student stats
    # We need to apply effective enrollments per course
    # Defer to feature engineering — for seed, just compute simple GPA + credits
    # _sync_student_stats from students.py would do it, but we recompute simpler here
    return len(enrollments_data), n_failed, 0


async def main(n_students: int = 1000):
    print(f"Seeding {n_students} synthetic students...")
    cohort_distribution = [2021, 2022, 2023, 2024]

    async with AsyncSessionLocal() as db:
        print("Step 1: Upserting courses...")
        courses = await upsert_courses(db)
        await db.commit()

        # Re-fetch courses after commit (need fresh session attachment)
        result = await db.execute(select(Course))
        courses = {c.course_code: c for c in result.scalars().all()}

        print(f"Step 2: Generating {n_students} students...")
        # Check existing SYN students
        result = await db.execute(
            select(Student).where(Student.mssv.like("SYN%"))
        )
        existing_count = len(result.scalars().all())
        if existing_count > 0:
            print(f"  ⚠️  Found {existing_count} existing SYN students. Run cleanup_synthetic.py first.")
            return

        total_enrollments = 0
        total_failed = 0

        # Batch in groups of 50 to keep transactions manageable
        BATCH = 50
        for batch_start in range(0, n_students, BATCH):
            batch_end = min(batch_start + BATCH, n_students)
            for i in range(batch_start + 1, batch_end + 1):
                cohort = cohort_distribution[(i - 1) % len(cohort_distribution)]
                n_e, n_f, _ = await generate_student(i, cohort, db, courses)
                total_enrollments += n_e
                total_failed += n_f
            await db.commit()
            print(f"  Generated {batch_end}/{n_students} ({total_enrollments} enrollments, {total_failed} failed)")

    print(f"\n✓ Done. {n_students} students, {total_enrollments} enrollments.")
    print("  Run _sync_student_stats via API to compute warning_levels:")
    print("  → Each /me/dashboard call will sync. Or trigger manually after.")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    asyncio.run(main(n))
