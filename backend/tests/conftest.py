import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.api.dependencies import get_db, get_session_factory
from app.config import settings
from app.database import database_models  # noqa: F401  (registers all tables)
from app.database.connection import Base
from app.main import app


@pytest.fixture()
def session_factory(tmp_path):
    """A real temp-file SQLite DB per test (separate connection per session, like production)."""
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _fk_on(conn, _rec):
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False)
    engine.dispose()


@pytest.fixture()
def db_session(session_factory):
    """For assertions in tests. Call db_session.expire_all() before re-reading changed rows."""
    session = session_factory()
    yield session
    session.close()


@pytest.fixture()
def client(session_factory):
    def _get_db():
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    # NOTE: not used as a context manager, so the startup hook (real meetwise.db) never runs in tests.
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def mock_mode(monkeypatch):
    monkeypatch.setattr(settings, "mock_mode", True)


@pytest.fixture()
def fake_keys(monkeypatch):
    monkeypatch.setattr(settings, "mock_mode", False)
    monkeypatch.setattr(settings, "tavily_api_key", "test-key")
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")


@pytest.fixture()
def valid_payload():
    return {
        "organization_or_person": "Stripe",
        "attendee_name": "Jane Doe",
        "meeting_date": "2026-11-20",
        "meeting_time": "10:30:00",
        "purpose": "Discuss a payments partnership",
    }
