"""
Xoá toàn bộ SV synthetic (MSSV bắt đầu bằng 'SYN').
Dùng raw DELETE để DB CASCADE tự xử lý enrollments.

Cách chạy:
  docker compose exec backend python -m scripts.cleanup_synthetic
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select, func

from app.db.session import AsyncSessionLocal
from app.models.student import Student
from app.models.user import User


async def main():
    async with AsyncSessionLocal() as db:
        # Count first
        result = await db.execute(
            select(func.count()).select_from(Student).where(Student.mssv.like("SYN%"))
        )
        count = result.scalar_one()
        if count == 0:
            print("Không tìm thấy SV synthetic nào.")
            return

        print(f"Tìm thấy {count} SV synthetic. Đang xoá...")

        # Delete students first (cascade enrollments via DB FK ondelete=CASCADE)
        await db.execute(delete(Student).where(Student.mssv.like("SYN%")))
        # Then delete users (Student.user_id FK has ondelete=CASCADE but user is parent)
        await db.execute(delete(User).where(User.email.like("%@synthetic.local")))
        await db.commit()

        print(f"✓ Đã xoá {count} students + users + cascade enrollments.")


if __name__ == "__main__":
    asyncio.run(main())
