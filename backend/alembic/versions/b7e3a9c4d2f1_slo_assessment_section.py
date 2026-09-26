"""slo_assessment_section

Revision ID: b7e3a9c4d2f1
Revises: f4d9c07a5b21
Create Date: 2026-09-26 00:00:00.000000

Issue #98 — an SLO assessment can name the section it measured. Marking
variance is a difference between two sections of one course on the same SLO in
the same semester, which a course-level roll-up cannot show. The column is
nullable: every assessment written before this migration is a course-level
roll-up and stays valid with the column null. Section-level rows sit alongside
the roll-up rather than replacing it.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b7e3a9c4d2f1'
down_revision: Union[str, None] = 'f4d9c07a5b21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'slo_assessments',
        sa.Column('section_id', sa.String(), nullable=True),
    )
    op.create_foreign_key(
        'slo_assessments_section_id_fkey',
        'slo_assessments',
        'schedule_sections',
        ['section_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'slo_assessments_section_id_fkey', 'slo_assessments', type_='foreignkey'
    )
    op.drop_column('slo_assessments', 'section_id')
