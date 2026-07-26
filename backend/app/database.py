import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

REPO_ROOT = Path(__file__).parent.parent.parent
DEFAULT_DOTENV = REPO_ROOT / ".env"
DEFAULT_DATABASE_URL = "postgresql://waleedkhalaf@/school_ai?host=/tmp"


def resolve_database_url(env_file: Path = DEFAULT_DOTENV) -> str:
    """
    The one answer to "which database?", shared by the app and by Alembic.

    Precedence: an explicit DATABASE_URL in the environment, then the repo's
    .env, then the built-in default. Alembic used to skip .env entirely and
    fall back to the port in alembic.ini, so `make migrate` on a machine with a
    local port override migrated whatever happened to answer on 5432.
    """
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    if env_file.exists():
        from_dotenv = dotenv_values(env_file).get("DATABASE_URL")
        if from_dotenv:
            return from_dotenv
    return DEFAULT_DATABASE_URL


DATABASE_URL = resolve_database_url()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
