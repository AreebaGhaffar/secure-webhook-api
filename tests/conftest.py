import os

# The environment must be set BEFORE the app is imported, so that the
# app connects to the TEST database and uses a known test secret.
from tests.helpers import TEST_SECRET

os.environ["WEBHOOK_SECRET"] = TEST_SECRET

from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.config import get_settings  # noqa: E402

TEST_DB_NAME = "webhook_test_db"


def _build_test_url() -> str:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return explicit
    base = make_url(get_settings().database_url)
    return base.set(database=TEST_DB_NAME).render_as_string(hide_password=False)


os.environ["DATABASE_URL"] = _build_test_url()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401
from app.database import Base, get_engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    Base.metadata.create_all(get_engine())
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    engine = get_engine()
    # Safety check: never wipe anything except a test database.
    assert "test" in engine.url.database, "Refusing to clean a non-test database"
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE webhook_events"))
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def process_calls(monkeypatch):
    """Records every time the business-processing step runs."""
    calls = []
    monkeypatch.setattr(
        "app.main.process_event", lambda event: calls.append(event.event_id)
    )
    return calls