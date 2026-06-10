import os
import json
import pytest
from pathlib import Path
from sqlalchemy import create_engine, text

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://waleedkhalaf@/school_ai_test?host=/tmp",
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

ZOOM_IN_STUDENTS = [
    "Waleed Khalaf",
    "Mariam Al-Kandari",
    "Fahad Al-Ajmi",
    "Noor Al-Hamad",
    "Omar Al-Mutairi",
]

ALL_TABLES = [
    "programs", "faculty", "students", "courses", "schedule_sections",
    "enrollments", "prerequisites", "lms_signals", "onboarding_tasks",
    "support_cases", "interventions", "sponsorship_records",
    "financial_aid_records", "administrative_holds", "graduation_requirements",
    "student_course_progress", "career_pathways", "alumni_mentors",
    "workflow_items", "slos", "slo_assessments", "cohort_slo_history",
    "student_slo_results",
]


@pytest.fixture(scope="module")
def engine():
    return create_engine(TEST_DATABASE_URL)


@pytest.fixture(autouse=True, scope="module")
def migrated_db(engine):
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import text as _text

    cfg = Config("/Users/waleedkhalaf/workspace/KBM/School-ai/backend/alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    cfg.set_main_option(
        "script_location",
        "/Users/waleedkhalaf/workspace/KBM/School-ai/backend/alembic",
    )

    def drop_enum():
        with engine.connect() as conn:
            conn.execute(_text("DROP TYPE IF EXISTS datasource CASCADE"))
            conn.commit()

    command.downgrade(cfg, "base")
    drop_enum()
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")
    drop_enum()


@pytest.fixture(autouse=True)
def truncate_between_tests(engine):
    yield
    with engine.connect() as conn:
        conn.execute(text(
            "TRUNCATE TABLE " + ", ".join(ALL_TABLES) + " CASCADE"
        ))
        conn.commit()


# ── Tracer bullet ──────────────────────────────────────────────────────────────

def test_seed_inserts_programs(engine):
    from app.seed import seed

    seed(TEST_DATABASE_URL, FIXTURES_DIR)

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM programs")).scalar()

    expected = len(json.loads((FIXTURES_DIR / "programs.json").read_text()))
    assert count == expected


# ── Full load ──────────────────────────────────────────────────────────────────

def test_seed_loads_all_tables(engine):
    from app.seed import seed

    seed(TEST_DATABASE_URL, FIXTURES_DIR)

    with engine.connect() as conn:
        for table in ALL_TABLES:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            assert count > 0, f"Table '{table}' is empty after seeding"


# ── Idempotency ────────────────────────────────────────────────────────────────

def test_seed_is_idempotent(engine):
    from app.seed import seed

    seed(TEST_DATABASE_URL, FIXTURES_DIR)
    counts_first = {}
    with engine.connect() as conn:
        for table in ALL_TABLES:
            counts_first[table] = conn.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            ).scalar()

    seed(TEST_DATABASE_URL, FIXTURES_DIR)
    with engine.connect() as conn:
        for table in ALL_TABLES:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            assert count == counts_first[table], (
                f"Table '{table}' count changed after second seed "
                f"({counts_first[table]} → {count})"
            )


# ── Zoom-in students ───────────────────────────────────────────────────────────

def test_zoom_in_students_present_after_seed(engine):
    from app.seed import seed

    seed(TEST_DATABASE_URL, FIXTURES_DIR)

    with engine.connect() as conn:
        names = {
            row[0]
            for row in conn.execute(text("SELECT name FROM students"))
        }

    for student in ZOOM_IN_STUDENTS:
        assert student in names, f"Zoom-in student '{student}' missing after seed"


# ── Validation: bad FK caught before writes ────────────────────────────────────

def test_seed_rejects_broken_foreign_key(engine, tmp_path):
    from app.seed import seed, SeedValidationError

    # Copy real fixtures then corrupt one student's program_id
    for f in FIXTURES_DIR.glob("*.json"):
        (tmp_path / f.name).write_text(f.read_text())

    students = json.loads((tmp_path / "students.json").read_text())
    students[0]["program_id"] = "prog_DOES_NOT_EXIST"
    (tmp_path / "students.json").write_text(json.dumps(students))

    with pytest.raises(SeedValidationError, match="program_id"):
        seed(TEST_DATABASE_URL, tmp_path)


def test_seed_makes_no_writes_when_validation_fails(engine, tmp_path):
    from app.seed import seed, SeedValidationError

    for f in FIXTURES_DIR.glob("*.json"):
        (tmp_path / f.name).write_text(f.read_text())

    students = json.loads((tmp_path / "students.json").read_text())
    students[0]["program_id"] = "prog_DOES_NOT_EXIST"
    (tmp_path / "students.json").write_text(json.dumps(students))

    with pytest.raises(SeedValidationError):
        seed(TEST_DATABASE_URL, tmp_path)

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM programs")).scalar()
    assert count == 0, "seed() wrote rows despite validation failure"
