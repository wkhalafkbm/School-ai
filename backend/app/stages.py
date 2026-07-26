"""
The journey stage vocabulary — issue #68.

One value per journey stage, named after the nav stage in Shell.tsx that owns
it. Everything that writes or reads a `stage` draws from here: the workflow
items agents and the UI create, the queries each stage page runs, the Overview
journey-health map and priority queue.

Before this module the repo carried two vocabularies — fixtures said
`academic_progress` where the write-tool spec said `academic_risk` — so an item
created by the Academic Risk page's own button was invisible to the Academic
Risk page. tests/test_stage_vocabulary.py fails if a fixture, the tool spec, a
query, or a frontend writer drifts off this set again.
"""

from enum import StrEnum


class Stage(StrEnum):
    admissions = "admissions"
    enrollment = "enrollment"
    teaching_readiness = "teaching_readiness"
    academic_risk = "academic_risk"
    progression = "progression"
    career_alumni = "career_alumni"


STAGES: frozenset[str] = frozenset(Stage)

# The stages the Overview journey-health map reports on. Teaching readiness is
# absent because its health is a property of a cohort, not of a student moving
# through the journey — the map's row is one status per student-facing stage.
JOURNEY_HEALTH_STAGES: tuple[Stage, ...] = (
    Stage.admissions,
    Stage.enrollment,
    Stage.academic_risk,
    Stage.progression,
    Stage.career_alumni,
)


class WorkflowStatus(StrEnum):
    """
    The lifecycle of a workflow item, as the Workflow Activity table renders it.

    `completed` is the terminal value; the write-tool spec used to document
    `complete`, which no frontend status map knew how to badge (#68).
    """

    pending = "pending"
    in_review = "in_review"
    in_progress = "in_progress"
    approved = "approved"
    completed = "completed"
    blocked = "blocked"
    overdue = "overdue"


WORKFLOW_STATUSES: frozenset[str] = frozenset(WorkflowStatus)

# Stage values retired by #68, mapped to their replacement. Read by the Alembic
# data migration and kept here so the guard test can assert no writer or reader
# still names one.
LEGACY_STAGES: dict[str, Stage] = {
    "onboarding": Stage.admissions,
    "registration": Stage.enrollment,
    "academic_progress": Stage.academic_risk,
    "graduation_planning": Stage.progression,
    "career": Stage.career_alumni,
}

LEGACY_STATUSES: dict[str, WorkflowStatus] = {
    "complete": WorkflowStatus.completed,
}
