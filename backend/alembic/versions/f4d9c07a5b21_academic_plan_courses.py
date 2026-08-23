"""academic_plan_courses

Revision ID: f4d9c07a5b21
Revises: e2c4b6a91d75
Create Date: 2026-08-23 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f4d9c07a5b21'
down_revision: Union[str, None] = 'e2c4b6a91d75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'academic_plan_courses',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('student_id', sa.String(), nullable=False),
        sa.Column('term', sa.String(), nullable=False),
        sa.Column('term_index', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.String(), nullable=False),
        # The offering, not the catalog entry, is what fixes the term and the
        # meeting pattern of a planned class.
        sa.Column('section_id', sa.String(), nullable=False),
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
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['section_id'], ['schedule_sections.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('academic_plan_courses')
