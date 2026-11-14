import hashlib
import hmac

SIGNATURE_PREFIX = "sha256="


def compute_signature(secret: str, raw_body: bytes) -> str:
    """Return the expected header value: 'sha256=<hex digest>'."""
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"{SIGNATURE_PREFIX}{digest}"


def verify_signature(secret: str, raw_body: bytes, signature_header: str | None) -> bool:
    """Check the signature using a constant-time comparison."""
    if not signature_header:
        return False
    expected = compute_signature(secret, raw_body)
    return hmac.compare_digest(
        expected.encode("utf-8"), signature_header.encode("utf-8")
    )