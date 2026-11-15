import json

from app.security import compute_signature

TEST_SECRET = "test_webhook_secret_for_pytest_only"


def make_event(event_id: str = "evt_test_1001") -> dict:
    return {
        "event_id": event_id,
        "event_type": "payment.completed",
        "created_at": "2026-11-08T10:30:00Z",
        "data": {
            "payment_id": "pay_test_5001",
            "amount": 2500,
            "currency": "USD",
            "status": "completed",
        },
    }


def to_body(event: dict) -> bytes:
    return json.dumps(event).encode("utf-8")


def signed_headers(body: bytes, secret: str = TEST_SECRET) -> dict:
    return {
        "Content-Type": "application/json",
        "X-Webhook-Signature": compute_signature(secret, body),
    }