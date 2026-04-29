from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.student import Student
    from app.models.course import Course


class EnrollmentStatus(str, enum.Enum):
    enrolled  = "enrolled"
    passed    = "passed"
    failed    = "failed"
    withdrawn = "withdrawn"
    exempt    = "exempt"


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        sa.UniqueConstraint("student_id", "course_id", "semester", name="uq_enrollment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    semester: Mapped[str] = mapped_column(sa.String(10), nullable=False)

    # ─── Điểm thành phần ────────────────────────────────────
    midterm_score: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    lab_score:     Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    other_score:   Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    final_score:   Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)

    # ─── Trọng số (tổng = 1.0) ──────────────────────────────
    midterm_weight: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0.3)
    lab_weight:     Mapped[float] = mapped_column(sa.Float, nullable=False, default=0.0)
    other_weight:   Mapped[float] = mapped_column(sa.Float, nullable=False, default=0.0)
    final_weight:   Mapped[float] = mapped_column(sa.Float, nullable=False, default=0.7)

    # ─── Điểm tổng kết ──────────────────────────────────────
    total_score:  Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    grade_letter: Mapped[Optional[str]]   = mapped_column(sa.String(3), nullable=True)

    status: Mapped[EnrollmentStatus] = mapped_column(
        sa.Enum(EnrollmentStatus, name="enrollmentstatus"),
        nullable=False,
        default=EnrollmentStatus.enrolled,
    )

    # ─── Metadata ───────────────────────────────────────────
    attendance_rate: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    is_finalized: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default="manual"
    )

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
    student: Mapped[Student] = relationship("Student", back_populates="enrollments")
    course: Mapped[Course]   = relationship("Course", back_populates="enrollments")
