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

REPO_ROOT = Path(__file__).parent.parent.parent
ENV_EXAMPLE = REPO_ROOT / ".env.example"


def test_the_built_in_default_is_the_one_env_example_documents():
    """
    A developer who never copied .env.example gets this fallback, so it has to
    be the database the project tells them to run — not a third answer that
    disagrees with both .env.example and docker-compose.
    """
    documented = dict(
        line.split("=", 1)
        for line in ENV_EXAMPLE.read_text().splitlines()
        if "=" in line and not line.startswith("#")
    )["DATABASE_URL"]
    assert DEFAULT_DATABASE_URL == documented


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
