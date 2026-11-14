from app.security import compute_signature, verify_signature

SECRET = "test_secret_for_unit_tests"
BODY = b'{"event_id": "evt_test_1001", "event_type": "payment.completed"}'


def test_valid_signature_is_accepted():
    header = compute_signature(SECRET, BODY)
    assert verify_signature(SECRET, BODY, header) is True


def test_wrong_secret_is_rejected():
    header = compute_signature("another_secret", BODY)
    assert verify_signature(SECRET, BODY, header) is False


def test_tampered_body_is_rejected():
    header = compute_signature(SECRET, BODY)
    assert verify_signature(SECRET, BODY + b" ", header) is False


def test_reformatted_json_is_rejected():
    """Same JSON content but different spacing is different bytes."""
    header = compute_signature(SECRET, b'{"a":1}')
    assert verify_signature(SECRET, b'{"a": 1}', header) is False


def test_missing_signature_is_rejected():
    assert verify_signature(SECRET, BODY, None) is False
    assert verify_signature(SECRET, BODY, "") is False


def test_header_without_prefix_is_rejected():
    header = compute_signature(SECRET, BODY).removeprefix("sha256=")
    assert verify_signature(SECRET, BODY, header) is False


def test_non_ascii_header_does_not_crash():
    assert verify_signature(SECRET, BODY, "sha256=é") is False