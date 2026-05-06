"""add_m5_rag_chatbot

Revision ID: 9a5d2e7c4b19
Revises: 331730d3032d
Create Date: 2026-05-04 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9a5d2e7c4b19"
down_revision: Union[str, None] = "331730d3032d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("page_number", sa.Integer(), nullable=True))
    op.add_column(
        "documents",
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_documents_source_file", "documents", ["source_file"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chat_messages_student_id"),
        "chat_messages",
        ["student_id"],
        unique=False,
    )
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_chat_messages_created_at", table_name="chat_messages")
    op.drop_index(op.f("ix_chat_messages_student_id"), table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_documents_source_file", table_name="documents")
    op.drop_column("documents", "metadata")
    op.drop_column("documents", "page_number")
