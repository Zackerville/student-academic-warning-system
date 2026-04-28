from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.student import Student


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    semester: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    risk_score: Mapped[float] = mapped_column(sa.Float, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        sa.Enum(RiskLevel, name="risklevel"), nullable=False
    )
    risk_factors: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    predicted_courses: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    # ─── Relationships ───────────────────────────────────────
    student: Mapped[Student] = relationship("Student", back_populates="predictions")
