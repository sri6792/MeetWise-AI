from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.database.connection import SessionLocal


def get_db() -> Iterator[Session]:
    """One database session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_factory():
    """Background research jobs open their own sessions. Overridable in tests."""
    return SessionLocal
