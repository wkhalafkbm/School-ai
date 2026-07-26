import os
import pytest
from sqlalchemy import create_engine, inspect, text
from alembic.config import Config
from alembic import command

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://waleedkhalaf@/school_ai_test?host=/tmp",
)

EXPECTED_TABLES = {
    "students", "programs", "courses", "faculty", "enrollments",
    "lms_signals", "onboarding_tasks", "prerequisites", "schedule_sections",
    "sponsorship_records", "financial_aid_records", "administrative_holds",
    "support_cases", "interventions", "graduation_requirements",
    "student_course_progress", "career_pathways", "alumni_mentors",
    "workflow_items", "slos", "slo_assessments", "cohort_slo_history",
    "student_slo_results", "student_term_gpa",
}


@pytest.fixture(scope="module")
def alembic_cfg():
    cfg = Config("/Users/waleedkhalaf/workspace/KBM/School-ai/backend/alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    cfg.set_main_option("script_location", "/Users/waleedkhalaf/workspace/KBM/School-ai/backend/alembic")
    return cfg


@pytest.fixture(scope="module")
def engine():
    return create_engine(TEST_DATABASE_URL)


def _drop_enum(engine):
    with engine.connect() as conn:
        conn.execute(text("DROP TYPE IF EXISTS datasource CASCADE"))
        conn.commit()


@pytest.fixture(autouse=True, scope="module")
def reset_db(alembic_cfg, engine):
    command.downgrade(alembic_cfg, "base")
    _drop_enum(engine)
    yield
    command.downgrade(alembic_cfg, "base")
    _drop_enum(engine)


def test_upgrade_creates_all_tables(alembic_cfg, engine):
    command.upgrade(alembic_cfg, "head")
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(tables), (
        f"Missing tables after upgrade: {EXPECTED_TABLES - tables}"
    )


def test_upgrade_applies_onto_an_already_migrated_database(alembic_cfg, engine):
    """A deployed DB upgrades in a separate process from the one that built it,
    so each step must be safe against schema objects that already exist."""
    command.downgrade(alembic_cfg, "base")
    _drop_enum(engine)

    command.upgrade(alembic_cfg, "c9e4d1f2a8b3")
    command.upgrade(alembic_cfg, "head")

    tables = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES.issubset(tables), (
        f"Missing tables after stepwise upgrade: {EXPECTED_TABLES - tables}"
    )


def test_upgrade_rewrites_retired_stage_and_status_values(alembic_cfg, engine):
    """
    Issue #68 — rows written before the vocabulary was unified still carry the
    retired values. A deployed database is upgraded, not re-seeded, so the
    migration itself has to move them or those rows stay invisible to the pages
    that now filter on the canonical stage.
    """
    command.downgrade(alembic_cfg, "base")
    _drop_enum(engine)
    command.upgrade(alembic_cfg, "d5a71b3c6e92")

    legacy_rows = [
        ("wfl-legacy-1", "academic_progress", "complete"),
        ("wfl-legacy-2", "registration", "pending"),
        ("wfl-legacy-3", "graduation_planning", "approved"),
        ("wfl-legacy-4", "career", "complete"),
        ("wfl-legacy-5", "onboarding", "pending"),
        ("wfl-legacy-6", "admissions", "in_review"),
    ]
    with engine.connect() as conn:
        for item_id, stage, status in legacy_rows:
            conn.execute(
                text(
                    "INSERT INTO workflow_items (id, stage, status, data_source) "
                    "VALUES (:id, :stage, :status, 'SIS')"
                ),
                {"id": item_id, "stage": stage, "status": status},
            )
        conn.commit()

    command.upgrade(alembic_cfg, "head")

    with engine.connect() as conn:
        migrated = dict(
            conn.execute(
                text(
                    "SELECT id, stage FROM workflow_items WHERE id LIKE 'wfl-legacy-%'"
                )
            ).fetchall()
        )
        statuses = dict(
            conn.execute(
                text(
                    "SELECT id, status FROM workflow_items WHERE id LIKE 'wfl-legacy-%'"
                )
            ).fetchall()
        )

    assert migrated == {
        "wfl-legacy-1": "academic_risk",
        "wfl-legacy-2": "enrollment",
        "wfl-legacy-3": "progression",
        "wfl-legacy-4": "career_alumni",
        "wfl-legacy-5": "admissions",
        "wfl-legacy-6": "admissions",
    }
    assert statuses == {
        "wfl-legacy-1": "completed",
        "wfl-legacy-2": "pending",
        "wfl-legacy-3": "approved",
        "wfl-legacy-4": "completed",
        "wfl-legacy-5": "pending",
        "wfl-legacy-6": "in_review",
    }


def test_downgrade_removes_all_tables(alembic_cfg, engine):
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    remaining = EXPECTED_TABLES & tables
    assert not remaining, f"Tables still present after downgrade: {remaining}"
