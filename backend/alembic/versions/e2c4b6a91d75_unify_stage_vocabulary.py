"""unify_stage_vocabulary

Issue #68 — workflow items were written with two competing stage vocabularies,
so an item created by the Academic Risk page was invisible to it. Move every
retired value onto the canonical one (app/stages.py) and settle the
`complete`/`completed` status split at the same time.

Revision ID: e2c4b6a91d75
Revises: d5a71b3c6e92
Create Date: 2026-07-26 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e2c4b6a91d75'
down_revision: Union[str, None] = 'd5a71b3c6e92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Retired value -> canonical value. Mirrors LEGACY_STAGES / LEGACY_STATUSES in
# app/stages.py, spelled out here because a migration must keep working after
# the application code it was written beside has moved on.
STAGE_RENAMES = {
    "onboarding": "admissions",
    "registration": "enrollment",
    "academic_progress": "academic_risk",
    "graduation_planning": "progression",
    "career": "career_alumni",
}

STATUS_RENAMES = {
    "complete": "completed",
}


def _rename(column: str, renames: dict[str, str]) -> None:
    for old, new in renames.items():
        op.execute(
            sa.text(
                f"UPDATE workflow_items SET {column} = :new WHERE {column} = :old"
            ).bindparams(new=new, old=old)
        )


def upgrade() -> None:
    _rename("stage", STAGE_RENAMES)
    _rename("status", STATUS_RENAMES)


def downgrade() -> None:
    # `onboarding` and `admissions` both became `admissions`, so the split
    # cannot be reconstructed; the reverse mapping restores the value each
    # canonical stage is named after and drops the ambiguity.
    reverse_stages = {
        new: old for old, new in STAGE_RENAMES.items() if old != "onboarding"
    }
    _rename("stage", reverse_stages)
    _rename("status", {new: old for old, new in STATUS_RENAMES.items()})
