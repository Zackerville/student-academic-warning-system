from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_code: Mapped[str] = mapped_column(
        sa.String(20), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    credits: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    faculty: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    # ─── Relationships ───────────────────────────────────────
    enrollments: Mapped[list[Enrollment]] = relationship(
        "Enrollment", back_populates="course"
    )
