from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.database import resolve_database_url

# A caller that supplied its own URL — the test suite pointing at a throwaway
# database — is left alone. Otherwise resolve it the way the app does, from
# DATABASE_URL or the repo's .env, so `alembic upgrade head` and the running
# backend can never disagree about which database they mean.
if not config.get_main_option("sqlalchemy.url", None):
    config.set_main_option("sqlalchemy.url", resolve_database_url())

from app.models import Base
target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
