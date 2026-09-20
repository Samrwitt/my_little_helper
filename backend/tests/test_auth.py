"""Auth and security unit tests (no database)."""

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify():
    hashed = hash_password("SecurePass123!")
    assert hashed != "SecurePass123!"
    assert verify_password("SecurePass123!", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    token = create_access_token("user-123", extra_claims={"email": "a@b.com"})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert payload["email"] == "a@b.com"


def test_refresh_token_type():
    token = create_refresh_token("user-123")
    payload = decode_token(token)
    assert payload["type"] == "refresh"
