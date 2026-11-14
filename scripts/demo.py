import json
import uuid
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.security import compute_signature

URL = "http://127.0.0.1:8000/webhooks"


def send(label: str, body: bytes, signature: str | None) -> None:
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Webhook-Signature"] = signature
    response = httpx.post(URL, content=body, headers=headers, timeout=10)
    print(f"{label}\n  -> {response.status_code} {response.text}\n")


def main() -> None:
    secret = get_settings().webhook_secret
    event_id = f"evt_demo_{uuid.uuid4().hex[:8]}"
    event = {
        "event_id": event_id,
        "event_type": "payment.completed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data": {
            "payment_id": "pay_test_5001",
            "amount": 2500,
            "currency": "USD",
            "status": "completed",
        },
    }
    body = json.dumps(event).encode("utf-8")
    good = compute_signature(secret, body)

    print(f"Demo event id: {event_id}\n")
    send("1. Valid signature, first delivery (expect 200 processed)", body, good)
    send("2. Same event again (expect 200 duplicate)", body, good)
    send("3. Wrong signature (expect 401)", body, compute_signature("wrong-secret", body))
    send("4. Missing signature (expect 401)", body, None)

    bad_payload = b'{"event_id": "evt_incomplete"}'
    send(
        "5. Signed, but required fields missing (expect 422)",
        bad_payload,
        compute_signature(secret, bad_payload),
    )
    not_json = b"this is not json"
    send(
        "6. Signed, but not JSON (expect 422)",
        not_json,
        compute_signature(secret, not_json),
    )


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print("Could not reach the server. Start it with: uvicorn app.main:app")