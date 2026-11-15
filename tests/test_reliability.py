from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.database import get_engine
from tests.helpers import make_event, signed_headers, to_body


def count_events() -> int:
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT count(*) FROM webhook_events")).scalar()


def test_database_failure_rolls_back_and_is_not_reported_as_success(
    client, monkeypatch
):
    body = to_body(make_event("evt_dbfail_1"))
    headers = signed_headers(body)

    def failing_commit(self):
        raise OperationalError("COMMIT", {}, Exception("simulated database failure"))

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", failing_commit)
        response = client.post("/webhooks", content=body, headers=headers)

    # No false success: the sender gets an error, so it will retry.
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "processed" not in response.text
    # Nothing was stored.
    assert count_events() == 0

    # Once the database works again, the retry is processed normally.
    retry = client.post("/webhooks", content=body, headers=headers)
    assert retry.status_code == 200
    assert retry.json() == {"status": "processed", "event_id": "evt_dbfail_1"}
    assert count_events() == 1