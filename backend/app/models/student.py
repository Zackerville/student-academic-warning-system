from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.enrollment import Enrollment
    from app.models.warning import Warning
    from app.models.prediction import Prediction
    from app.models.notification import Notification
    from app.models.chat_message import ChatMessage


class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    mssv: Mapped[str] = mapped_column(
        sa.String(20), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    faculty: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    major: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    cohort: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    gpa_cumulative: Mapped[float] = mapped_column(
        sa.Float, nullable=False, default=0.0
    )
    credits_earned: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    warning_level: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ─── Relationships ───────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="student")
    enrollments: Mapped[list[Enrollment]] = relationship(
        "Enrollment", back_populates="student", cascade="all, delete-orphan"
    )
    warnings: Mapped[list[Warning]] = relationship(
        "Warning", back_populates="student", cascade="all, delete-orphan"
    )
    predictions: Mapped[list[Prediction]] = relationship(
        "Prediction", back_populates="student", cascade="all, delete-orphan"
    )
    notifications: Mapped[list[Notification]] = relationship(
        "Notification", back_populates="student", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list[ChatMessage]] = relationship(
        "ChatMessage", back_populates="student", cascade="all, delete-orphan"
    )
