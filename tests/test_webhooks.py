import pytest
from sqlalchemy import text

from app.database import get_engine
from tests.helpers import make_event, signed_headers, to_body


def count_events() -> int:
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT count(*) FROM webhook_events")).scalar()


def test_valid_signature_creates_one_event(client, process_calls):
    body = to_body(make_event("evt_valid_1"))

    response = client.post("/webhooks", content=body, headers=signed_headers(body))

    assert response.status_code == 200
    assert response.json() == {"status": "processed", "event_id": "evt_valid_1"}
    assert count_events() == 1
    with get_engine().connect() as conn:
        row = conn.execute(
            text(
                "SELECT status, processed_at FROM webhook_events "
                "WHERE event_id = 'evt_valid_1'"
            )
        ).one()
    assert row.status == "processed"
    assert row.processed_at is not None
    assert process_calls == ["evt_valid_1"]


def test_invalid_signature_is_rejected(client, process_calls):
    body = to_body(make_event("evt_badsig_1"))

    response = client.post(
        "/webhooks", content=body, headers=signed_headers(body, secret="wrong-secret")
    )

    assert response.status_code == 401
    assert count_events() == 0
    assert process_calls == []


def test_missing_signature_is_rejected(client, process_calls):
    body = to_body(make_event("evt_nosig_1"))

    response = client.post(
        "/webhooks", content=body, headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 401
    assert count_events() == 0
    assert process_calls == []


def test_signature_is_checked_before_payload_validation(client):
    body = b"this is not json"

    response = client.post(
        "/webhooks", content=body, headers=signed_headers(body, secret="wrong-secret")
    )

    assert response.status_code == 401
    assert count_events() == 0


def test_duplicate_event_is_not_processed_again(client, process_calls):
    body = to_body(make_event("evt_dup_1"))
    headers = signed_headers(body)

    first = client.post("/webhooks", content=body, headers=headers)
    second = client.post("/webhooks", content=body, headers=headers)

    assert first.status_code == 200
    assert first.json()["status"] == "processed"
    assert second.status_code == 200
    assert second.json() == {"status": "duplicate", "event_id": "evt_dup_1"}
    assert count_events() == 1
    assert process_calls == ["evt_dup_1"]


def test_different_events_are_stored_separately(client, process_calls):
    for event_id in ("evt_a", "evt_b"):
        body = to_body(make_event(event_id))
        response = client.post("/webhooks", content=body, headers=signed_headers(body))
        assert response.json()["status"] == "processed"

    assert count_events() == 2
    assert process_calls == ["evt_a", "evt_b"]


@pytest.mark.parametrize(
    "bad_body",
    [
        b"this is not json",
        b'{"event_id": "evt_incomplete"}',
        b'{"event_id": "evt_x", "event_type": "t", '
        b'"created_at": "2026-11-08T10:30:00Z", "data": []}',
    ],
    ids=["not-json", "missing-fields", "data-is-a-list"],
)
def test_malformed_payload_returns_422(client, process_calls, bad_body):
    response = client.post(
        "/webhooks", content=bad_body, headers=signed_headers(bad_body)
    )

    assert response.status_code == 422
    assert count_events() == 0
    assert process_calls == []