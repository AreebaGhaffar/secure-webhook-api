import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture
def no_env_file(monkeypatch, tmp_path):
    """Run from an empty folder so your real .env file is not found."""
    monkeypatch.chdir(tmp_path)


def test_all_settings_missing_gives_clear_error(monkeypatch, no_env_file):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)

    with pytest.raises(RuntimeError) as error:
        get_settings()

    message = str(error.value)
    assert "DATABASE_URL" in message
    assert "WEBHOOK_SECRET" in message
    assert ".env.example" in message


@pytest.mark.parametrize("missing", ["DATABASE_URL", "WEBHOOK_SECRET"])
def test_each_missing_setting_is_named(monkeypatch, no_env_file, missing):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5433/x")
    monkeypatch.setenv("WEBHOOK_SECRET", "some-secret")
    monkeypatch.delenv(missing)

    with pytest.raises(RuntimeError, match=missing):
        get_settings()


def test_app_refuses_to_start_without_configuration(monkeypatch, no_env_file):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="Missing or invalid required configuration"):
        with TestClient(app):
            pass