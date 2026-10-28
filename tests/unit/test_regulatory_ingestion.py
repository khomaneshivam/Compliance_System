"""
Unit Tests for Regulatory Ingestion, Source Classification, and Error Sanitization
Verifies error categories, leak prevention (no raw tracebacks or file paths),
and adapter/provider mode classification.
"""

import socket
import pytest
from unittest.mock import MagicMock

from app.modules.regulatory_intel.safeguards import (
    sanitize_source_error,
    FileSizeExceededError,
    MalformedFileError,
    IngestionSecurityError,
    SourceUnavailableError,
)
from app.modules.documents.safeguards import (
    sanitize_document_error,
    FileSizeLimitExceededError,
    MalformedDocumentError,
    EmptyDocumentError,
    ProhibitedFileTypeError,
    DocumentSecurityError,
)
from app.modules.regulatory_intel.pipeline import compute_source_adapter_mode
from app.modules.documents.router import (
    get_document_provider_mode,
    get_document_error_category,
)


# ------------------------------------------------------------------------------
# 1. Regulatory Source Error Sanitization (All 8 Categories)
# ------------------------------------------------------------------------------

def test_sanitize_source_error_payload_oversized():
    exc = FileSizeExceededError(size_bytes=30 * 1024 * 1024, max_bytes=25 * 1024 * 1024)
    category, msg = sanitize_source_error(exc)
    assert category == "PAYLOAD_OVERSIZED"
    assert "25 MB" in msg
    assert "30" not in msg  # No unvetted user input leak


def test_sanitize_source_error_malformed_stream():
    exc = MalformedFileError("Corrupted stream header at offset 0x44")
    category, msg = sanitize_source_error(exc)
    assert category == "MALFORMED_STREAM"
    assert "damaged" in msg.lower() or "binary headers" in msg.lower()
    assert "0x44" not in msg


def test_sanitize_source_error_security_blocked():
    exc = IngestionSecurityError("SSRF attempt to access http://169.254.169.254")
    category, msg = sanitize_source_error(exc)
    assert category == "SECURITY_BLOCKED"
    assert "169.254.169.254" not in msg  # No sensitive target IP leak


def test_sanitize_source_error_timeout():
    exc = TimeoutError("HTTP request to portal timed out after 30000ms")
    category, msg = sanitize_source_error(exc)
    assert category == "TIMEOUT"
    assert "timed out" in msg.lower()


def test_sanitize_source_error_network_unreachable():
    for exc in [
        ConnectionError("Failed to establish a new connection: [Errno 111] Connection refused"),
        socket.error("Host is down"),
        Exception("Network is unreachable"),
    ]:
        category, msg = sanitize_source_error(exc)
        assert category == "NETWORK_UNREACHABLE"
        assert "network connection failed" in msg.lower() or "unreachable" in msg.lower()


def test_sanitize_source_error_service_throttled():
    for exc in [
        SourceUnavailableError("MPCB portal returned HTTP 503 Service Unavailable"),
        Exception("Rate limit exceeded (429 Too Many Requests)"),
        Exception("HTTP 503 backend throttled"),
    ]:
        category, msg = sanitize_source_error(exc)
        assert category == "SERVICE_THROTTLED"
        assert "unavailable" in msg.lower() or "throttle" in msg.lower()


def test_sanitize_source_error_extraction_parse_error():
    exc = ValueError("Failed to extract compliance parameters from circular text")
    category, msg = sanitize_source_error(exc)
    assert category == "EXTRACTION_PARSE_ERROR"
    assert "parsed" in msg.lower() or "compliance parameters" in msg.lower()


def test_sanitize_source_error_internal_and_leak_prevention():
    raw_sensitive_trace = (
        'Traceback (most recent call last):\n'
        '  File "D:\\Complaince System\\app\\modules\\regulatory_intel\\pipeline.py", line 42, in fetch\n'
        '    raise OperationalError("SELECT * FROM credentials WHERE key=\'secret_prod_key\'")'
    )
    exc = Exception(raw_sensitive_trace)
    category, msg = sanitize_source_error(exc)
    assert category == "INTERNAL_PROCESSING_ERROR"
    # Verify zero leak of local paths, code, or secret SQL queries
    assert "Traceback" not in msg
    assert "D:\\" not in msg
    assert "pipeline.py" not in msg
    assert "credentials" not in msg
    assert "secret_prod_key" not in msg


# ------------------------------------------------------------------------------
# 2. Document Processing Error Sanitization
# ------------------------------------------------------------------------------

def test_sanitize_document_error_categories():
    test_cases = [
        (FileSizeLimitExceededError("30MB"), "PAYLOAD_OVERSIZED"),
        (MalformedDocumentError("Broken PDF xref table"), "MALFORMED_STREAM"),
        (EmptyDocumentError("0 bytes"), "EMPTY_DOCUMENT"),
        (ProhibitedFileTypeError("Executable binary .exe"), "SECURITY_BLOCKED"),
        (DocumentSecurityError("Disallowed mime"), "SECURITY_BLOCKED"),
        (Exception("Adversarial prompt injection attempt detected"), "PROMPT_INJECTION_SUSPECTED"),
        (Exception("Unable to extract table clauses"), "EXTRACTION_PARSE_ERROR"),
        (Exception("Local I/O error at D:\\vault\\tenants\\tenant_1\\doc.pdf"), "INTERNAL_PROCESSING_ERROR"),
    ]
    for exc, expected_category in test_cases:
        category, msg = sanitize_document_error(exc)
        assert category == expected_category
        # Must not leak path or code
        assert "D:\\" not in msg
        assert "xref" not in msg


# ------------------------------------------------------------------------------
# 3. Regulatory Source Adapter Mode Classification
# ------------------------------------------------------------------------------

def test_compute_source_adapter_mode():
    source = MagicMock()

    # Disabled source
    source.is_active = False
    source.health_status = "HEALTHY"
    source.consecutive_failures = 0
    assert compute_source_adapter_mode(source) == "DISABLED"

    # Failed source (health_status UNAVAILABLE or failures >= 3)
    source.is_active = True
    source.health_status = "UNAVAILABLE"
    source.consecutive_failures = 0
    assert compute_source_adapter_mode(source) == "FAILED"

    source.health_status = "HEALTHY"
    source.consecutive_failures = 3
    assert compute_source_adapter_mode(source) == "FAILED"

    # Local fixture source
    source.consecutive_failures = 0
    source.health_status = "HEALTHY"
    source.adapter_type = "LOCAL_FIXTURE"
    source.url = "fixture://regulatory-vault/demo-feed"
    assert compute_source_adapter_mode(source) == "FIXTURE"

    source.adapter_type = "SCRAPER"
    source.url = "fixture://egazette/circulars"
    assert compute_source_adapter_mode(source) == "FIXTURE"

    # Live HTTP source
    source.adapter_type = "OFFICIAL_PORTAL"
    source.url = "https://mpcb.gov.in/circulars"
    assert compute_source_adapter_mode(source) == "LIVE_HTTP"


# ------------------------------------------------------------------------------
# 4. Document Extraction Provider Mode Disclosure
# ------------------------------------------------------------------------------

def test_get_document_provider_mode():
    doc = MagicMock()

    # Extraction failed
    doc.extraction_status = "EXTRACTION_FAILED"
    doc.extracted_metadata = {"provider_mode": "LIVE_OCR"}
    assert get_document_provider_mode(doc) == "FAILED"

    # Completed with LIVE_OCR
    doc.extraction_status = "EXTRACTED"
    doc.extracted_metadata = {"provider_mode": "LIVE_OCR"}
    assert get_document_provider_mode(doc) == "LIVE_OCR"

    # Completed with FIXTURE
    doc.extraction_status = "EXTRACTED"
    doc.extracted_metadata = {"provider_mode": "FIXTURE"}
    assert get_document_provider_mode(doc) == "FIXTURE"

    # Default fallback when metadata is empty
    doc.extraction_status = "PENDING"
    doc.extracted_metadata = {}
    assert get_document_provider_mode(doc) == "FIXTURE"


def test_get_document_error_category():
    doc = MagicMock()

    # Pre-calculated error category in metadata
    doc.extracted_metadata = {"error_category": "SECURITY_BLOCKED"}
    doc.extraction_error = "Disallowed MIME"
    assert get_document_error_category(doc) == "SECURITY_BLOCKED"

    # Derived dynamically from extraction_error
    doc.extracted_metadata = {}
    doc.extraction_error = "File size exceeds limit of 25MB"
    assert get_document_error_category(doc) == "PAYLOAD_OVERSIZED"

    # None when no error
    doc.extracted_metadata = {}
    doc.extraction_error = None
    assert get_document_error_category(doc) is None
