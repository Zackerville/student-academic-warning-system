from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class EventType(str, enum.Enum):
    exam = "exam"
    submission = "submission"
    activity = "activity"
    evaluation = "evaluation"


class TargetAudience(str, enum.Enum):
    all = "all"
    faculty_specific = "faculty_specific"
    cohort_specific = "cohort_specific"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    event_type: Mapped[EventType] = mapped_column(
        sa.Enum(EventType, name="eventtype"), nullable=False
    )
    target_audience: Mapped[TargetAudience] = mapped_column(
        sa.Enum(TargetAudience, name="targetaudience"),
        nullable=False,
        default=TargetAudience.all,
    )
    target_value: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    start_time: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    is_mandatory: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    # ─── Relationships ───────────────────────────────────────
    creator: Mapped[Optional[User]] = relationship("User", back_populates="created_events")
