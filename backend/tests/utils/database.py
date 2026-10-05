from pathlib import Path

from alembic import command
from alembic.config import Config
from pydantic import PostgresDsn, TypeAdapter
from testcontainers.community.postgres import PostgresContainer

from app.core.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[2]
POSTGRES_IMAGE = "pgvector/pgvector:pg18"

_container: PostgresContainer | None = None


def start_test_database() -> None:
    """Start a throwaway pgvector Postgres, point settings at it, and migrate it.

    Must run before `app.core.db` is imported: it builds its engine from `settings`.
    The suite's teardown deletes every user, so it must never see development data.
    """
    global _container
    _container = PostgresContainer(POSTGRES_IMAGE, dbname="test", driver="psycopg")
    _container.start()
    settings.DATABASE_URL = TypeAdapter(PostgresDsn).validate_python(
        _container.get_connection_url()
    )

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "app" / "alembic"))
    command.upgrade(config, "head")


def stop_test_database() -> None:
    global _container
    if _container is not None:
        _container.stop()
        _container = None
