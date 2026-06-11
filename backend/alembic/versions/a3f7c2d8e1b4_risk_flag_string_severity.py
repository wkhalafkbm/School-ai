"""risk_flag_string_severity

Revision ID: a3f7c2d8e1b4
Revises: 8118123df9b9
Create Date: 2026-06-11 16:19:46.624172

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a3f7c2d8e1b4'
down_revision: Union[str, None] = '8118123df9b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "lms_signals",
        "risk_flag",
        type_=sa.String(10),
        postgresql_using="CASE WHEN risk_flag THEN 'high' ELSE 'none' END",
        existing_nullable=True,
    )
    op.alter_column("lms_signals", "risk_flag", server_default="none")


def downgrade() -> None:
    # Drop the string default before changing type — PostgreSQL can't auto-cast 'none' to boolean
    op.alter_column("lms_signals", "risk_flag", server_default=None)
    op.alter_column(
        "lms_signals",
        "risk_flag",
        type_=sa.Boolean(),
        postgresql_using="risk_flag != 'none'",
        existing_nullable=True,
    )
    op.alter_column("lms_signals", "risk_flag", server_default=sa.false())
