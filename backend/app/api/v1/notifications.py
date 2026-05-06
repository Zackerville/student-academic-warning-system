"""
Notifications API (M6.3) — /api/v1/notifications

Endpoints:
- GET    /notifications/me                 — list (filter unread/all)
- GET    /notifications/me/unread-count    — số chưa đọc cho bell badge
- PUT    /notifications/me/{id}/read       — mark 1 noti read
- PUT    /notifications/me/read-all        — mark hết
- GET    /notifications/me/preferences     — lấy email preference
- PUT    /notifications/me/preferences     — toggle email opt-in/out
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_student, get_current_user, get_db
from app.models.student import Student
from app.models.user import User
from app.schemas.notification import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services import notification as notification_service
from app.services import warning_engine

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/me", response_model=list[NotificationResponse])
async def list_my_notifications(
    only_unread: bool = Query(False, description="Chỉ trả notification chưa đọc"),
    limit: int = Query(50, ge=1, le=200),
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    await warning_engine.sync_current_warning_level(db, student)

    return await notification_service.list_for_student(
        db, student.id, only_unread=only_unread, limit=limit
    )


@router.get("/me/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    await warning_engine.sync_current_warning_level(db, student)

    count = await notification_service.unread_count(db, student.id)
    return UnreadCountResponse(unread=count)


@router.put("/me/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    notification_id: UUID,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    ok = await notification_service.mark_read(
        db, notification_id=notification_id, student_id=student.id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")
    return {"message": "Đã đánh dấu đã đọc"}


@router.put("/me/read-all", response_model=dict)
async def mark_all_notifications_read(
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    count = await notification_service.mark_all_read(db, student.id)
    return {"data": {"marked": count}, "message": f"Đã đánh dấu {count} thông báo đã đọc"}


@router.get("/me/preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    user: User = Depends(get_current_user),
):
    return NotificationPreferenceResponse(
        email_notifications_enabled=user.email_notifications_enabled
    )


@router.put("/me/preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    payload: NotificationPreferenceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await notification_service.update_email_preference(
        db, user_id=user.id, enabled=payload.email_notifications_enabled
    )
    return NotificationPreferenceResponse(
        email_notifications_enabled=payload.email_notifications_enabled
    )
