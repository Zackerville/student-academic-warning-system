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
    from app.models.student import Student


class WarningCreatedBy(str, enum.Enum):
    system = "system"
    admin = "admin"


class Warning(Base):
    __tablename__ = "warnings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    semester: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    reason: Mapped[str] = mapped_column(sa.Text, nullable=False)
    gpa_at_warning: Mapped[float] = mapped_column(sa.Float, nullable=False)
    ai_risk_score: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[WarningCreatedBy] = mapped_column(
        sa.Enum(WarningCreatedBy, name="warningcreatedby"),
        nullable=False,
        default=WarningCreatedBy.system,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    # ─── Relationships ───────────────────────────────────────
    student: Mapped[Student] = relationship("Student", back_populates="warnings")
