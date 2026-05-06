"""
Notification service — CRUD + dispatcher cho in-app + email (M6.2).

Architecture:
- create() là single entry point để mọi nơi tạo notification.
- create() tự quyết định có gửi email không, dựa vào:
  - notification.type ∈ {warning, event, reminder} (system thì chỉ in-app)
  - user.email_notifications_enabled
  - settings.EMAIL_ENABLED
- Email gửi qua email_service.fire_and_forget — không block API caller.
- Email log vào notifications.email_sent_at sau khi spawn task.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification import Notification, NotificationType
from app.models.student import Student
from app.models.user import User
from app.services import email_service


# ─── CRUD ──────────────────────────────────────────────────────


async def create(
    *,
    db: AsyncSession,
    student: Student,
    type: NotificationType,
    title: str,
    content: str,
    email_template: Optional[str] = None,
    email_subject: Optional[str] = None,
    email_context: Optional[dict[str, Any]] = None,
    skip_email: bool = False,
) -> Notification:
    """
    Tạo notification + dispatch email (nếu bật).

    Args:
        student: Student đã loaded với user relationship (selectinload).
        skip_email: True nếu caller đã tự gửi email (vd warning_engine handle template phức tạp).
    """
    notification = Notification(
        student_id=student.id, type=type, title=title, content=content
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    if skip_email:
        return notification

    if email_template and email_subject:
        await _maybe_send_email(
            db=db,
            student=student,
            notification=notification,
            template=email_template,
            subject=email_subject,
            context=email_context or {},
        )

    return notification


async def _maybe_send_email(
    *,
    db: AsyncSession,
    student: Student,
    notification: Notification,
    template: str,
    subject: str,
    context: dict[str, Any],
) -> None:
    user = await _resolve_user(db, student)
    if not user:
        return
    if not user.email_notifications_enabled:
        logger.info(
            f"[notification] Skip email — student={student.mssv} opted out"
        )
        return
    if not user.email or "@" not in user.email:
        return

    enriched = {
        "full_name": student.full_name,
        "mssv": student.mssv,
        **context,
    }
    email_service.fire_and_forget(
        to=user.email,
        subject=subject,
        template_name=template,
        context=enriched,
    )
    notification.email_sent_at = datetime.now(tz=timezone.utc)
    await db.commit()


async def _resolve_user(db: AsyncSession, student: Student) -> Optional[User]:
    loaded_user = student.__dict__.get("user")
    if loaded_user is not None:
        return loaded_user
    result = await db.execute(select(User).where(User.id == student.user_id))
    return result.scalar_one_or_none()


# ─── List / read ──────────────────────────────────────────────


async def list_for_student(
    db: AsyncSession,
    student_id: UUID,
    *,
    only_unread: bool = False,
    limit: int = 50,
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.student_id == student_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if only_unread:
        stmt = stmt.where(Notification.is_read == False)  # noqa: E712
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def unread_count(db: AsyncSession, student_id: UUID) -> int:
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.student_id == student_id,
            Notification.is_read == False,  # noqa: E712
        )
    )
    return int(result.scalar() or 0)


async def mark_read(
    db: AsyncSession, *, notification_id: UUID, student_id: UUID
) -> bool:
    result = await db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.student_id == student_id,
        )
        .values(is_read=True)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return (result.rowcount or 0) > 0


async def mark_all_read(db: AsyncSession, student_id: UUID) -> int:
    result = await db.execute(
        update(Notification)
        .where(
            Notification.student_id == student_id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return int(result.rowcount or 0)


# ─── Preferences ──────────────────────────────────────────────


async def update_email_preference(
    db: AsyncSession, *, user_id: UUID, enabled: bool
) -> bool:
    result = await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(email_notifications_enabled=enabled)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return (result.rowcount or 0) > 0
