from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(768), nullable=True)
    source_file: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    chunk_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    # ─── Relationships ───────────────────────────────────────
    uploader: Mapped[Optional[User]] = relationship(
        "User", back_populates="uploaded_documents"
    )
