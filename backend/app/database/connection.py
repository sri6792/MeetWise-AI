"""SQLAlchemy engine, session factory and declarative Base."""
import logging

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

if _is_sqlite:
    # SQLite ignores foreign keys unless this is switched on for every connection
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create all tables (idempotent). Called once at application startup."""
    from app.database import database_models  # noqa: F401  (registers the models)

    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def _add_missing_columns() -> None:
    """Lightweight dev migration: if a table already exists but a newer model added
    nullable columns, ALTER TABLE them in. (Alembic can replace this later.)"""
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            existing = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing:
                    continue
                if not col.nullable:
                    logger.warning("Cannot auto-add NOT NULL column %s.%s", table.name, col.name)
                    continue
                ddl = col.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {ddl}'))
                logger.info("Added column %s.%s", table.name, col.name)
