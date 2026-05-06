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
    from app.models.event import Event
    from app.models.document import Document
    from app.models.student import Student


class UserRole(str, enum.Enum):
    student = "student"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        sa.String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        sa.Enum(UserRole, name="userrole"),
        nullable=False,
        default=UserRole.student,
    )
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    email_notifications_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=True, server_default=sa.true()
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    # ─── Relationships ───────────────────────────────────────
    student: Mapped[Student] = relationship("Student", back_populates="user", uselist=False)
    created_events: Mapped[list[Event]] = relationship("Event", back_populates="creator")
    uploaded_documents: Mapped[list[Document]] = relationship(
        "Document", back_populates="uploader"
    )