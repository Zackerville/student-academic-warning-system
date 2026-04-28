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
    enrolled = "enrolled"
    passed = "passed"
    failed = "failed"
    withdrawn = "withdrawn"


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
    midterm_score: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    final_score: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    total_score: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    grade_letter: Mapped[Optional[str]] = mapped_column(sa.String(3), nullable=True)
    status: Mapped[EnrollmentStatus] = mapped_column(
        sa.Enum(EnrollmentStatus, name="enrollmentstatus"),
        nullable=False,
        default=EnrollmentStatus.enrolled,
    )
    attendance_rate: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
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
    course: Mapped[Course] = relationship("Course", back_populates="enrollments")
