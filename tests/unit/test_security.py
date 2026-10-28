"""
Unit Tests for Security, Password Hashing, and JWT Tokens
"""

from datetime import timedelta
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)


def test_password_hashing_and_verification():
    raw_password = "SecureCompliancePassword2026!"
    hashed = get_password_hash(raw_password)
    
    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_generation_and_decoding():
    user_id = "test-user-uuid-1234"
    claims = {"role": "PLANT_MANAGER", "tenant_id": "tenant-uuid-5678"}
    
    token = create_access_token(subject=user_id, claims=claims)
    assert isinstance(token, str)
    
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["role"] == "PLANT_MANAGER"
    assert payload["tenant_id"] == "tenant-uuid-5678"


def test_expired_jwt_token_rejection():
    user_id = "test-expired-user"
    expired_token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(seconds=-10)  # already expired
    )
    payload = decode_access_token(expired_token)
    assert payload is None
