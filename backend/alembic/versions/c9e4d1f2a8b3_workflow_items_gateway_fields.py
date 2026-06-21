"""workflow_items_gateway_fields

Revision ID: c9e4d1f2a8b3
Revises: a3f7c2d8e1b4
Create Date: 2026-06-21 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c9e4d1f2a8b3'
down_revision: Union[str, None] = 'a3f7c2d8e1b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workflow_items", sa.Column("stage", sa.String(), nullable=True))
    op.add_column("workflow_items", sa.Column("trigger", sa.String(), nullable=True))
    op.add_column("workflow_items", sa.Column("owner_name", sa.String(), nullable=True))
    op.add_column("workflow_items", sa.Column("owner_role", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("workflow_items", "owner_role")
    op.drop_column("workflow_items", "owner_name")
    op.drop_column("workflow_items", "trigger")
    op.drop_column("workflow_items", "stage")
