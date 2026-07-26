"""student_term_gpa

Revision ID: d5a71b3c6e92
Revises: c9e4d1f2a8b3
Create Date: 2026-07-26 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd5a71b3c6e92'
down_revision: Union[str, None] = 'c9e4d1f2a8b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'student_term_gpa',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('student_id', sa.String(), nullable=False),
        sa.Column('term', sa.String(), nullable=False),
        sa.Column('term_index', sa.Integer(), nullable=False),
        sa.Column('term_gpa', sa.Float(), nullable=True),
        sa.Column('cumulative_gpa', sa.Float(), nullable=True),
        # The datasource enum was created by the initial schema migration;
        # create_type=False keeps this step from re-issuing CREATE TYPE.
        sa.Column(
            'data_source',
            postgresql.ENUM(
                'SIS', 'LMS', 'demo', name='datasource', create_type=False
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('student_term_gpa')
