from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.student import Student


class NotificationType(str, enum.Enum):
    warning = "warning"
    reminder = "reminder"
    event = "event"
    system = "system"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[NotificationType] = mapped_column(
        sa.Enum(NotificationType, name="notificationtype"), nullable=False
    )
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    sent_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    # ─── Relationships ───────────────────────────────────────
    student: Mapped[Student] = relationship("Student", back_populates="notifications")
