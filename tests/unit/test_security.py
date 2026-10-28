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


# ==============================================================================
# Configuration Hardening & Secret Validation Tests
# ==============================================================================

import secrets
import pytest
from pydantic import ValidationError
from app.core.config import Settings, KNOWN_PLACEHOLDER_SECRETS


def test_settings_development_allows_convenient_defaults():
    """Verifies that development mode accepts default placeholder secrets and debug settings."""
    cfg = Settings(
        ENVIRONMENT="development",
        DEBUG=True,
        SECRET_KEY="demo-insecure-secret-key-change-in-production-plantproof-compliance",
        SEED_DEMO_USERS=True,
    )
    assert cfg.ENVIRONMENT == "development"
    assert cfg.DEBUG is True
    assert cfg.SECRET_KEY.startswith("demo-insecure")
    assert cfg.SEED_DEMO_USERS is True


def test_settings_production_rejects_placeholder_secret():
    """Verifies that production mode strictly refuses known placeholder and default JWT secrets."""
    for placeholder in KNOWN_PLACEHOLDER_SECRETS:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                ENVIRONMENT="production",
                DEBUG=False,
                SECRET_KEY=placeholder,
                SEED_DEMO_USERS=False,
            )
        err_msg = str(exc_info.value)
        assert (
            "Production environment must not use placeholder or weak JWT secret keys" in err_msg
            or "String should have at least 16 characters" in err_msg
        )


def test_settings_production_rejects_short_secret():
    """Verifies production mode rejects secrets shorter than 32 characters."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="short-secret-1234567890",
            SEED_DEMO_USERS=False,
        )
    assert "Production environment must not use placeholder or weak JWT secret keys" in str(exc_info.value)


def test_settings_production_rejects_unsafe_debug():
    """Verifies production mode refuses DEBUG=True."""
    secure_key = secrets.token_hex(32)
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DEBUG=True,
            SECRET_KEY=secure_key,
            SEED_DEMO_USERS=False,
        )
    assert "DEBUG must be set to False in production" in str(exc_info.value)


def test_settings_production_rejects_demo_users_seeding():
    """Verifies production mode refuses SEED_DEMO_USERS=True."""
    secure_key = secrets.token_hex(32)
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY=secure_key,
            SEED_DEMO_USERS=True,
        )
    assert "SEED_DEMO_USERS must not be True in production" in str(exc_info.value)


def test_settings_production_accepts_valid_configuration():
    """Verifies production mode succeeds with high-entropy secret, DEBUG=False, SEED_DEMO_USERS=False."""
    secure_key = secrets.token_hex(32)
    cfg = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY=secure_key,
        SEED_DEMO_USERS=False,
    )
    assert cfg.ENVIRONMENT == "production"
    assert cfg.DEBUG is False
    assert cfg.SECRET_KEY == secure_key


def test_signing_secret_is_not_mutated_or_regenerated_on_boot():
    """Verifies that Settings uses the explicitly supplied secret without persisting or mutating it."""
    provided_key = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
    cfg = Settings(
        ENVIRONMENT="development",
        SECRET_KEY=provided_key,
    )
    assert cfg.SECRET_KEY == provided_key

