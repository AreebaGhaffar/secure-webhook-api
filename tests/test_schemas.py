import pytest
from pydantic import ValidationError

from app.schemas import WebhookEventIn

VALID = {
    "event_id": "evt_test_1001",
    "event_type": "payment.completed",
    "created_at": "2026-11-08T10:30:00Z",
    "data": {
        "payment_id": "pay_test_5001",
        "amount": 2500,
        "currency": "USD",
        "status": "completed",
    },
}


def test_valid_event_is_accepted():
    event = WebhookEventIn.model_validate(VALID)
    assert event.event_id == "evt_test_1001"
    assert event.data["amount"] == 2500


@pytest.mark.parametrize("field", ["event_id", "event_type", "created_at", "data"])
def test_missing_required_field_is_rejected(field):
    body = dict(VALID)
    body.pop(field)
    with pytest.raises(ValidationError):
        WebhookEventIn.model_validate(body)


@pytest.mark.parametrize("bad_data", [[], "text", 5])
def test_data_must_be_a_json_object(bad_data):
    with pytest.raises(ValidationError):
        WebhookEventIn.model_validate({**VALID, "data": bad_data})


def test_empty_event_id_is_rejected():
    with pytest.raises(ValidationError):
        WebhookEventIn.model_validate({**VALID, "event_id": ""})


def test_event_id_too_long_is_rejected():
    with pytest.raises(ValidationError):
        WebhookEventIn.model_validate({**VALID, "event_id": "x" * 256})


def test_event_type_too_long_is_rejected():
    with pytest.raises(ValidationError):
        WebhookEventIn.model_validate({**VALID, "event_type": "x" * 101})


def test_event_id_must_be_text():
    with pytest.raises(ValidationError):
        WebhookEventIn.model_validate({**VALID, "event_id": 123})


def test_invalid_created_at_is_rejected():
    with pytest.raises(ValidationError):
        WebhookEventIn.model_validate({**VALID, "created_at": "not-a-date"})