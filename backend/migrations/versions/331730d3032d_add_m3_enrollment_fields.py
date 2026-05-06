"""add_m3_enrollment_fields

Revision ID: 331730d3032d
Revises: e55f5d666040
Create Date: 2026-04-29 08:38:40.383770

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision: str = '331730d3032d'
down_revision: Union[str, None] = 'e55f5d666040'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'exempt' to the enrollmentstatus enum
    op.execute("ALTER TYPE enrollmentstatus ADD VALUE IF NOT EXISTS 'exempt'")

    op.add_column('enrollments', sa.Column('lab_score', sa.Float(), nullable=True))
    op.add_column('enrollments', sa.Column('other_score', sa.Float(), nullable=True))
    op.add_column('enrollments', sa.Column('midterm_weight', sa.Float(), nullable=False, server_default='0.3'))
    op.add_column('enrollments', sa.Column('lab_weight', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('enrollments', sa.Column('other_weight', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('enrollments', sa.Column('final_weight', sa.Float(), nullable=False, server_default='0.7'))
    op.add_column('enrollments', sa.Column('is_finalized', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('enrollments', sa.Column('source', sa.String(length=20), nullable=False, server_default='manual'))


def downgrade() -> None:
    op.drop_column('enrollments', 'source')
    op.drop_column('enrollments', 'is_finalized')
    op.drop_column('enrollments', 'final_weight')
    op.drop_column('enrollments', 'other_weight')
    op.drop_column('enrollments', 'lab_weight')
    op.drop_column('enrollments', 'midterm_weight')
    op.drop_column('enrollments', 'other_score')
    op.drop_column('enrollments', 'lab_score')