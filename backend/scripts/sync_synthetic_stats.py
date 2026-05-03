"""
Sync `gpa_cumulative`, `credits_earned`, `warning_level` cho mọi SV synthetic.
Áp dụng quy chế HCMUT highest-wins + thêm noise vào label để tránh deterministic.

Cách chạy:
  docker compose exec backend python -m scripts.sync_synthetic_stats
"""
from __future__ import annotations

import asyncio
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1.students import (
    _effective_enrollments_per_course,
    _enrollment_gpa_point,
)
from app.db.session import AsyncSessionLocal
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.student import Student
from app.services.gpa_calculator import _SPECIAL_LETTERS

random.seed(42)


def warning_level_from_gpa_noisy(
    gpa: float,
    attendance: float,
    unresolved_failed_total: int,
    unresolved_failed_retake_count: int = 0,
) -> int:
    """
    Probabilistic warning level — phản ánh thực tế quy chế + admin discretion.
    Thêm noise để label không deterministic 100% từ GPA → F1 không phải 1.0.

    Factors phụ ngoài GPA:
      - low attendance, nhiều môn chưa qua → tăng warning chance
      - học lại nhưng vẫn chưa qua → tăng warning chance
      - môn từng F nhưng đã học lại đạt không còn bị xem là rủi ro hiện tại
    """
    risk_boost = 0.0
    if attendance < 70:
        risk_boost += 0.10
    if unresolved_failed_total >= 3:
        risk_boost += 0.10
    if unresolved_failed_total >= 6:
        risk_boost += 0.10
    if unresolved_failed_retake_count >= 2:
        risk_boost += 0.10
    if unresolved_failed_retake_count >= 4:
        risk_boost += 0.10

    if gpa < 0.8:
        return 3
    if gpa < 1.0:
        return 2 if random.random() < 0.92 else 3
    if gpa < 1.2:
        return 1 if random.random() < 0.88 else (2 if random.random() < 0.5 else 0)
    if gpa < 1.5:
        return 1 if random.random() < (0.10 + risk_boost) else 0
    if gpa < 2.0:
        return 1 if random.random() < (0.05 + risk_boost) else 0
    if gpa < 2.5:
        # Range mới — SV có struggle history vẫn có risk
        return 1 if random.random() < (risk_boost * 0.6) else 0
    if gpa < 3.0:
        return 1 if random.random() < (risk_boost * 0.3) else 0
    return 0  # GPA >= 3.0 → an toàn


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Student).where(Student.mssv.like("SYN%"))
        )
        students = result.scalars().all()
        print(f"Syncing stats cho {len(students)} SV synthetic...")

        warning_dist = {0: 0, 1: 0, 2: 0, 3: 0}

        for i, student in enumerate(students, 1):
            # Fetch enrollments
            er = await db.execute(
                select(Enrollment)
                .where(Enrollment.student_id == student.id)
                .options(selectinload(Enrollment.course))
            )
            enrollments = er.scalars().all()

            effective = _effective_enrollments_per_course(enrollments)

            # Credits earned
            passed = {EnrollmentStatus.passed, EnrollmentStatus.exempt}
            credits = sum(
                e.course.credits for e in effective
                if e.status in passed and e.course.credits > 0
            )

            # GPA cumulative
            total_pts = 0.0
            total_tc = 0
            for e in effective:
                if e.course.credits == 0:
                    continue
                if e.grade_letter and e.grade_letter in _SPECIAL_LETTERS:
                    continue
                pt = _enrollment_gpa_point(e)
                if pt is None:
                    continue
                total_pts += pt * e.course.credits
                total_tc += e.course.credits

            gpa = round(total_pts / total_tc, 2) if total_tc > 0 else 0.0

            # Compute helpers for noisy warning logic
            failed_total = sum(1 for e in effective if e.status == EnrollmentStatus.failed)
            rates = [e.attendance_rate for e in enrollments if e.attendance_rate is not None]
            avg_attendance = sum(rates) / len(rates) if rates else 80.0

            # Failed retake count: chỉ đếm môn từng F, đã học lại, nhưng điểm hiệu lực vẫn F.
            by_course: dict = {}
            for e in enrollments:
                if e.course.credits == 0:
                    continue
                if e.grade_letter or e.total_score is not None:
                    by_course.setdefault(e.course_id, []).append(e)
            effective_by_course = {e.course_id: e for e in effective}
            failed_retake_count = sum(
                1 for attempts in by_course.values()
                if (
                    len(attempts) >= 2
                    and any(a.status == EnrollmentStatus.failed for a in attempts)
                    and effective_by_course.get(attempts[0].course_id) is not None
                    and effective_by_course[attempts[0].course_id].status == EnrollmentStatus.failed
                )
            )

            wlevel = warning_level_from_gpa_noisy(gpa, avg_attendance, failed_total, failed_retake_count)

            student.gpa_cumulative = gpa
            student.credits_earned = credits
            student.warning_level = wlevel
            warning_dist[wlevel] = warning_dist.get(wlevel, 0) + 1

            if i % 100 == 0:
                await db.commit()
                print(f"  Synced {i}/{len(students)}")

        await db.commit()

    print("\n✓ Done. Warning level distribution:")
    print(f"  Level 0 (Bình thường):      {warning_dist[0]} ({warning_dist[0]/10:.1f}%)")
    print(f"  Level 1 (Cảnh báo 1):       {warning_dist[1]} ({warning_dist[1]/10:.1f}%)")
    print(f"  Level 2 (Cảnh báo 2):       {warning_dist[2]} ({warning_dist[2]/10:.1f}%)")
    print(f"  Level 3 (Buộc thôi học):    {warning_dist[3]} ({warning_dist[3]/10:.1f}%)")
    positive = warning_dist[1] + warning_dist[2] + warning_dist[3]
    print(f"  → Positive class (warned >= 1): {positive} ({positive/10:.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())
