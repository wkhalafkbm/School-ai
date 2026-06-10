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
    "student_slo_results",
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


def test_downgrade_removes_all_tables(alembic_cfg, engine):
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    remaining = EXPECTED_TABLES & tables
    assert not remaining, f"Tables still present after downgrade: {remaining}"
