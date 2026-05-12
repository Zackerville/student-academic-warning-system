"""add_m9_schedule_fields

Revision ID: 8c1f3a7e9d4b
Revises: 7f4a8b1c2d3e
Create Date: 2026-05-12 16:30:00.000000

M9 schedule feature:
- students.timetable_json JSONB NULL — TKB đã parse từ myBK
- students.exam_schedule_json JSONB NULL — Lịch thi đã parse từ myBK
- students.personal_events_json JSONB NULL — Sự kiện cá nhân SV tự thêm
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "8c1f3a7e9d4b"
down_revision: Union[str, None] = "7f4a8b1c2d3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column("timetable_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "students",
        sa.Column("exam_schedule_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "students",
        sa.Column("personal_events_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("students", "personal_events_json")
    op.drop_column("students", "exam_schedule_json")
    op.drop_column("students", "timetable_json")
