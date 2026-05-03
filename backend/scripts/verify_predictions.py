"""
Verify M4 — chứng minh AI predict khác nhau cho SV có hồ sơ khác nhau.

Cách chạy:
  docker compose exec backend python -m scripts.verify_predictions

Output: bảng so sánh 8 SV (4 tier khác nhau) — features + risk_score + factors.
SV xuất sắc (GPA 3+) phải có risk thấp; SV cực yếu (GPA <1) phải có risk cao.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.ai.prediction.features import extract_features_for_student_id
from app.ai.prediction.model import prediction_service
from app.db.session import AsyncSessionLocal
from app.models.student import Student


def bar(value: float, max_value: float = 1.0, width: int = 30) -> str:
    """ASCII bar chart."""
    pct = min(1.0, max(0.0, value / max_value))
    filled = int(pct * width)
    return "█" * filled + "░" * (width - filled)


async def main():
    if not prediction_service.is_loaded:
        prediction_service.load()
    if not prediction_service.is_loaded:
        print("❌ Model chưa train. Chạy: docker compose exec backend python -m app.ai.prediction.train")
        return

    print(f"\n=== M4 VERIFICATION — Threshold {prediction_service.threshold} ===")
    print("Lấy 8 SV synthetic ngẫu nhiên (2 mỗi tier GPA) để so sánh.\n")

    async with AsyncSessionLocal() as db:
        # Pick 2 SV mỗi tier theo GPA range
        tiers = [
            ("Xuất sắc (GPA >= 3.5)", select(Student).where(Student.gpa_cumulative >= 3.5).where(Student.mssv.like("SYN%")).limit(2)),
            ("Trung bình (2.0-3.0)", select(Student).where(Student.gpa_cumulative.between(2.0, 3.0)).where(Student.mssv.like("SYN%")).limit(2)),
            ("Yếu (1.2-1.8)",        select(Student).where(Student.gpa_cumulative.between(1.2, 1.8)).where(Student.mssv.like("SYN%")).limit(2)),
            ("Cực yếu (< 1.0)",      select(Student).where(Student.gpa_cumulative < 1.0).where(Student.mssv.like("SYN%")).limit(2)),
        ]

        rows = []
        for tier_name, q in tiers:
            result = await db.execute(q)
            for s in result.scalars().all():
                feats = await extract_features_for_student_id(s.id, db)
                if feats is None:
                    continue
                pred = await prediction_service.predict_for_student(s, db, save=False)
                if pred is None:
                    continue
                await db.refresh(s)
                rows.append({
                    "tier": tier_name,
                    "mssv": s.mssv,
                    "gpa": s.gpa_cumulative,
                    "credits": s.credits_earned,
                    "warning_level": s.warning_level,
                    "failed": int(feats["unresolved_failed_courses"]),
                    "trend": -feats["gpa_trend_drop"],
                    "risk_score": pred.risk_score,
                    "risk_level": pred.risk_level.value,
                    "top_factors": pred.risk_factors["factors"][:3],
                })

        # Print summary table
        print(f"{'Tier':<25} {'MSSV':<10} {'GPA':>5} {'TC':>4} {'Warn':>4} {'Failed':>6} {'Trend':>6} {'Risk':>6} {'Level':<10} Bar")
        print("─" * 130)
        for r in rows:
            risk_bar = bar(r["risk_score"], 1.0, 25)
            print(
                f"{r['tier']:<25} {r['mssv']:<10} "
                f"{r['gpa']:>5.2f} {r['credits']:>4d} {r['warning_level']:>4d} "
                f"{r['failed']:>6d} {r['trend']:>6.2f} "
                f"{r['risk_score']*100:>5.1f}% {r['risk_level']:<10} {risk_bar}"
            )

        # Sanity check
        print("\n=== SANITY CHECKS ===")
        excellent = [r for r in rows if "Xuất sắc" in r["tier"]]
        critical = [r for r in rows if "Cực yếu" in r["tier"]]
        if excellent and critical:
            avg_excellent = sum(r["risk_score"] for r in excellent) / len(excellent)
            avg_critical = sum(r["risk_score"] for r in critical) / len(critical)
            diff = avg_critical - avg_excellent
            check_pass = avg_critical > avg_excellent + 0.4  # ít nhất 40% cao hơn
            mark = "✓" if check_pass else "✗"
            print(f"  {mark} Avg risk Cực yếu ({avg_critical*100:.1f}%) > Xuất sắc ({avg_excellent*100:.1f}%) + 40% margin")
            print(f"     Diff: {diff*100:.1f}% — {'PASS' if check_pass else 'FAIL — cần debug'}")

        # Check monotonicity: risk should generally decrease với GPA tăng
        sorted_by_gpa = sorted(rows, key=lambda r: r["gpa"])
        print(f"\n  Monotonic check (theo GPA tăng dần):")
        for r in sorted_by_gpa:
            print(f"    GPA {r['gpa']:.2f} → Risk {r['risk_score']*100:>5.1f}% [{r['risk_level']}]")

        # Show factor differences
        print("\n=== FACTOR COMPARISON (top 3 cho mỗi SV) ===")
        for r in rows:
            print(f"\n  {r['mssv']} (GPA {r['gpa']}, Risk {r['risk_score']*100:.1f}%):")
            for f in r["top_factors"]:
                print(f"    {f['impact_str']:>6} {f['label']}")


if __name__ == "__main__":
    asyncio.run(main())
