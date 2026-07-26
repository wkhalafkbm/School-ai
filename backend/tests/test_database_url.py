"""
Where the database URL comes from.

The repo used to answer this three different ways — alembic.ini said port 5432,
app/database.py said a local socket, and .env said whatever the developer runs
locally. `make migrate` took alembic.ini's answer, so a developer with a local
override silently migrated a database that was not theirs.
"""

from pathlib import Path

import pytest

from app.database import DEFAULT_DATABASE_URL, resolve_database_url

DOTENV_URL = "postgresql://uniai:uniai@localhost:5433/uniaidb"
EXPLICIT_URL = "postgresql://someone@/other_db?host=/tmp"


@pytest.fixture
def dotenv(tmp_path: Path) -> Path:
    path = tmp_path / ".env"
    path.write_text(f"UNIVERSITY_NAME=Demo\nDATABASE_URL={DOTENV_URL}\n")
    return path


def test_an_explicit_variable_wins_over_the_dotenv_file(monkeypatch, dotenv):
    """CI and the test suite pass the URL in the environment; that must win."""
    monkeypatch.setenv("DATABASE_URL", EXPLICIT_URL)
    assert resolve_database_url(dotenv) == EXPLICIT_URL


def test_the_dotenv_file_is_read_when_no_variable_is_set(monkeypatch, dotenv):
    """The case `make migrate` used to get wrong."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert resolve_database_url(dotenv) == DOTENV_URL


def test_the_documented_default_applies_when_there_is_no_dotenv(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert resolve_database_url(tmp_path / "absent.env") == DEFAULT_DATABASE_URL


def test_a_dotenv_without_a_database_url_falls_through(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    partial = tmp_path / ".env"
    partial.write_text("UNIVERSITY_NAME=Demo\n")
    assert resolve_database_url(partial) == DEFAULT_DATABASE_URL
