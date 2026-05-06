"""add_m6_warnings_email_fields

Revision ID: 7f4a8b1c2d3e
Revises: 9a5d2e7c4b19
Create Date: 2026-05-05 18:00:00.000000

M6 migration:
- notifications.email_sent_at TIMESTAMP NULL — log thời điểm gửi email (NULL = chưa gửi hoặc opt-out)
- users.email_notifications_enabled BOOLEAN DEFAULT TRUE — SV có thể opt-out email
- warnings.notification_id UUID NULL FK — link warning → notification để mark read sync
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f4a8b1c2d3e"
down_revision: Union[str, None] = "9a5d2e7c4b19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "users",
        sa.Column(
            "email_notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    op.add_column(
        "warnings",
        sa.Column("notification_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_warnings_notification_id",
        "warnings",
        "notifications",
        ["notification_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_warnings_notification_id", "warnings", type_="foreignkey")
    op.drop_column("warnings", "notification_id")
    op.drop_column("users", "email_notifications_enabled")
    op.drop_column("notifications", "email_sent_at")
