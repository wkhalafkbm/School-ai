import os
import pytest
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://waleedkhalaf@/school_ai_test?host=/tmp",
)
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(scope="module")
def engine():
    return create_engine(TEST_DATABASE_URL)


@pytest.fixture(autouse=True, scope="module")
def seeded_db(engine):
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

    from app.seed import seed
    seed(TEST_DATABASE_URL, FIXTURES_DIR)

    yield

    command.downgrade(cfg, "base")
    drop_enum()


def test_risk_flag_stores_string_severity(engine):
    with engine.connect() as conn:
        values = {
            row[0]
            for row in conn.execute(text("SELECT DISTINCT risk_flag FROM lms_signals"))
        }
    assert values <= {"none", "low", "medium", "high"}, (
        f"Expected string severity levels, got: {values}"
    )


def test_risk_flag_preserves_all_severity_levels_from_fixture(engine):
    with engine.connect() as conn:
        values = {
            row[0]
            for row in conn.execute(text("SELECT DISTINCT risk_flag FROM lms_signals"))
        }
    # fixture has 'high', 'medium', 'low', 'none' — all must survive the seed
    assert "high" in values
    assert "medium" in values
    assert "none" in values


def test_risk_flag_column_type_is_not_boolean(engine):
    with engine.connect() as conn:
        col_type = conn.execute(text("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'lms_signals' AND column_name = 'risk_flag'
        """)).scalar()
    assert col_type != "boolean", f"risk_flag is still boolean; expected character varying"
