"""Document AI provider-mode safety tests.

Synthetic document values are fixtures, not production evidence.
"""

import pytest

from app.core.config import Settings
from app.modules.documents.ai_service import (
    DisabledDocumentAIProvider,
    DocumentAIUnavailableError,
    MockSyntheticDocumentAIProvider,
    build_document_ai_provider,
)


def test_fixture_provider_is_available_in_development_and_test_only():
    assert isinstance(build_document_ai_provider("fixture", "development"), MockSyntheticDocumentAIProvider)
    assert isinstance(build_document_ai_provider("fixture", "test"), MockSyntheticDocumentAIProvider)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_fixture_provider_is_rejected_outside_development(environment):
    with pytest.raises(RuntimeError, match="prohibited outside development/test"):
        build_document_ai_provider("fixture", environment)


def test_disabled_provider_fails_closed_without_synthetic_fields():
    provider = build_document_ai_provider("disabled", "production")
    assert isinstance(provider, DisabledDocumentAIProvider)
    with pytest.raises(DocumentAIUnavailableError, match="no approved live provider"):
        provider.extract_document([], "sample-boiler-certificate.pdf")


def test_live_provider_mode_is_not_claimed_until_adapter_is_registered():
    with pytest.raises(RuntimeError, match="no reviewed live provider adapter"):
        build_document_ai_provider("live", "production")


def test_production_settings_reject_fixture_ai_even_with_strong_signing_secret():
    with pytest.raises(ValueError, match="synthetic document-AI fixtures are prohibited"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="a" * 64,
            SEED_DEMO_USERS=False,
            NOTIFICATION_DELIVERY_MODE="smtp",
            SMTP_HOST="smtp.example.com",
            PUBLIC_APP_URL="https://app.example.com",
            DOCUMENT_AI_PROVIDER_MODE="fixture",
        )


def test_production_can_start_with_document_ai_disabled():
    settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="b" * 64,
        SEED_DEMO_USERS=False,
        DOCUMENT_AI_PROVIDER_MODE="disabled",
    )
    assert settings.DOCUMENT_AI_PROVIDER_MODE == "disabled"
