from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config.settings import settings
from app.security.tokens import TokenError, create_token, decode_access_token


def test_create_and_decode_roundtrip():
    token = create_token(subject=42)
    claims = decode_access_token(token)
    assert claims["sub"] == "42"
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert claims["exp"] > claims["iat"]


def test_subject_is_coerced_to_string():
    # JWT spec defines "sub" as a string (or any JSON value, but conventionally string).
    token = create_token(subject=7)
    assert decode_access_token(token)["sub"] == "7"


def test_extra_claims_are_included():
    token = create_token(subject="user-1", extra_claims={"role": "admin", "scope": "read"})
    claims = decode_access_token(token)
    assert claims["role"] == "admin"
    assert claims["scope"] == "read"


def test_decode_rejects_garbage_token():
    with pytest.raises(TokenError):
        decode_access_token("not.a.valid.token")


def test_decode_rejects_tampered_payload():
    # Re-encode the token's payload with a different secret -> signature mismatch.
    token = create_token(subject="alice")
    claims = decode_access_token(token)
    forged = jwt.encode(
        {**claims, "sub": "attacker"},
        "different-secret",
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(TokenError):
        decode_access_token(forged)


def test_decode_rejects_expired_token():
    # Manually craft an already-expired token using the real secret.
    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {"sub": "x", "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(TokenError):
        decode_access_token(expired)
