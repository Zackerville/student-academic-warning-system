"""
Warnings API (M6.3) — /api/v1/warnings

Endpoints:
- GET    /warnings/me                — list cảnh báo của SV hiện tại
- GET    /warnings/me/{id}           — chi tiết 1 cảnh báo
- PATCH  /warnings/me/{id}/resolve   — SV mark resolved (vd đã liên hệ cố vấn)
- POST   /warnings/batch-run         — [admin] trigger batch check toàn trường
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_student, get_db, require_admin
from app.models.student import Student
from app.models.user import User
from app.models.warning import Warning
from app.schemas.warning import WarningResolve, WarningResponse
from app.services import warning_engine

router = APIRouter(prefix="/warnings", tags=["warnings"])


@router.get("/me", response_model=list[WarningResponse])
async def list_my_warnings(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    await warning_engine.sync_current_warning_level(db, student)

    result = await db.execute(
        select(Warning)
        .where(Warning.student_id == student.id)
        .order_by(Warning.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/me/{warning_id}", response_model=WarningResponse)
async def get_my_warning(
    warning_id: UUID,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    await warning_engine.sync_current_warning_level(db, student)

    result = await db.execute(
        select(Warning).where(
            Warning.id == warning_id, Warning.student_id == student.id
        )
    )
    warning = result.scalar_one_or_none()
    if not warning:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảnh báo")
    return warning


@router.patch("/me/{warning_id}/resolve", response_model=WarningResponse)
async def resolve_my_warning(
    warning_id: UUID,
    payload: WarningResolve,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """SV tự đánh dấu đã xử lý cảnh báo (vd đã liên hệ cố vấn)."""
    await warning_engine.sync_current_warning_level(db, student)

    result = await db.execute(
        select(Warning).where(
            Warning.id == warning_id, Warning.student_id == student.id
        )
    )
    warning = result.scalar_one_or_none()
    if not warning:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảnh báo")
    warning.is_resolved = payload.is_resolved
    await db.commit()
    await db.refresh(warning)
    return warning


@router.post("/batch-run", status_code=status.HTTP_202_ACCEPTED)
async def admin_batch_run_warnings(
    semester: str = Query(..., description="HK cần check, vd 242"),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin trigger batch check warnings cho toàn bộ SV trong 1 HK."""
    stats = await warning_engine.batch_check_warnings(db, semester)
    return {"data": stats, "message": f"Đã check {stats['checked']} SV cho HK {semester}"}
