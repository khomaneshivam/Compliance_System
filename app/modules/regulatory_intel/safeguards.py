"""
Regulatory Ingestion Safeguards & Security Boundaries
Enforces anti-SSRF, safe path handling, file size/MIME boundaries,
prompt injection neutralization, and robust regulatory date parsing.
"""

import ipaddress
import re
import socket
from datetime import date, datetime
from typing import Optional, Tuple
from urllib.parse import urlparse

from app.core.exceptions import AppException


class IngestionSecurityError(AppException):
    def __init__(self, message: str, code: str = "INGESTION_SECURITY_ERROR"):
        super().__init__(code=code, message=message, status_code=400)


class SourceUnavailableError(AppException):
    def __init__(self, message: str):
        super().__init__(
            code="SOURCE_UNAVAILABLE",
            message=message,
            status_code=503,
            remediation="Regulator portal is temporarily unreachable. Verify network status or retry later."
        )


class FileSizeExceededError(IngestionSecurityError):
    def __init__(self, size_bytes: int, max_bytes: int):
        super().__init__(
            message=f"File size of {size_bytes} bytes exceeds the strict security limit of {max_bytes} bytes.",
            code="FILE_SIZE_LIMIT_EXCEEDED"
        )


class MalformedFileError(IngestionSecurityError):
    def __init__(self, message: str):
        super().__init__(message=message, code="MALFORMED_FILE_ERROR")


# Maximum allowable document size: 25 MB
MAX_DOCUMENT_SIZE_BYTES = 25 * 1024 * 1024

# Allowed content MIME types
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/html",
    "application/xhtml+xml",
    "text/plain",
    "application/json",
}

# Forbidden URL schemes
ALLOWED_SCHEMES = {"http", "https", "fixture"}

# Prohibited IP networks (Loopback, RFC-1918, Cloud Metadata, Multicast)
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),   # AWS/GCP/Azure link-local metadata
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),        # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),       # IPv6 Link-Local
]


def validate_safe_url(url: str) -> str:
    """
    Validates a URL against Server-Side Request Forgery (SSRF).
    Blocks private IP ranges, loopbacks, link-local addresses, and non-HTTP protocols.
    Allows 'fixture://' for internal zero-dependency testing.
    """
    if not url or not isinstance(url, str):
        raise IngestionSecurityError("Invalid or empty URL provided.")

    clean_url = url.strip()
    parsed = urlparse(clean_url)

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise IngestionSecurityError(
            f"URL scheme '{parsed.scheme}' is prohibited. Only HTTP, HTTPS, or fixture URIs are allowed."
        )

    # Fixture URIs for local testing are safe
    if parsed.scheme.lower() == "fixture":
        return clean_url

    hostname = parsed.hostname
    if not hostname:
        raise IngestionSecurityError(f"URL '{url}' does not contain a valid hostname.")

    # Disallow explicit localhost names
    if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise IngestionSecurityError(f"Access to localhost or loopback address '{hostname}' is strictly blocked.")

    # Check if hostname is an IP literal
    try:
        ip = ipaddress.ip_address(hostname)
        for net in BLOCKED_NETWORKS:
            if ip in net:
                raise IngestionSecurityError(
                    f"Direct access to private or metadata IP '{ip}' is blocked by anti-SSRF policy."
                )
        return clean_url
    except ValueError:
        pass  # Hostname is a domain name, proceed to DNS resolution

    # Resolve hostname to verify destination IP is not private
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip = ipaddress.ip_address(ip_str)
            for net in BLOCKED_NETWORKS:
                if ip in net:
                    raise IngestionSecurityError(
                        f"Resolved IP '{ip}' for hostname '{hostname}' is in private or metadata subnet."
                    )
    except socket.gaierror:
        # If DNS fails in testing or disconnected mode, permit safe domains but block internal/metadata patterns
        if any(h in hostname.lower() for h in ("internal", "local", "corp", "metadata", "169.254")):
            raise IngestionSecurityError(f"Hostname '{hostname}' matches prohibited internal network patterns.")

    return clean_url


def sanitize_filename(filename: str) -> str:
    """Prevents directory traversal attacks by stripping path separators and non-whitelisted characters."""
    # Strip any directory path components
    base = filename.replace("\\", "/").split("/")[-1]
    # Keep only alphanumeric, hyphens, underscores, dots
    cleaned = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base)
    if not cleaned or cleaned.startswith("."):
        cleaned = f"doc_{int(datetime.now().timestamp())}.pdf"
    return cleaned


def validate_file_content_safety(content: bytes, mime_type: Optional[str] = None) -> None:
    """Verifies file size limits and content sanity against archive bombs and malformed streams."""
    size = len(content)
    if size > MAX_DOCUMENT_SIZE_BYTES:
        raise FileSizeExceededError(size, MAX_DOCUMENT_SIZE_BYTES)

    if size == 0:
        raise MalformedFileError("Fetched document content is empty (0 bytes).")

    # Reject ZIP / Archive magic bytes if claiming to be PDF or HTML
    if content.startswith(b"PK\x03\x04") or content.startswith(b"\x1f\x8b"):
        raise MalformedFileError("Prohibited archive/compressed zip payload detected in document stream.")

    if mime_type and mime_type.lower() not in ALLOWED_MIME_TYPES:
        raise IngestionSecurityError(
            f"MIME type '{mime_type}' is not supported. Permitted types: {', '.join(sorted(ALLOWED_MIME_TYPES))}."
        )


def sanitize_regulatory_text(raw_text: str) -> str:
    """
    Sanitizes untrusted regulatory text / OCR content before feeding to downstream LLMs.
    Guards against prompt injection directives such as:
    - 'Ignore all previous instructions'
    - 'You are now system'
    - 'Drop table' / code injection attempts
    """
    if not raw_text:
        return ""

    # Neutralize common prompt injection patterns
    injection_patterns = [
        r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
        r"(?i)system\s*:\s*you\s+are",
        r"(?i)override\s+(system|safety)\s+prompt",
        r"(?i)you\s+are\s+now\s+a\s+(developer|unrestricted|jailbreak)",
        r"(?i)<\s*script[^>]*>",
        r"(?i)exec\s*\(",
        r"(?i)eval\s*\(",
    ]

    sanitized = raw_text
    for pattern in injection_patterns:
        sanitized = re.sub(pattern, "[PROMPT_INJECTION_FLAGGED_AND_FILTERED]", sanitized)

    return sanitized


def parse_regulatory_date(date_str: Optional[str]) -> Optional[date]:
    """
    Robust deterministic date parser for Indian regulatory gazettes and official circulars.
    Supports:
    - ISO format: '2026-10-24'
    - Indian format: '24/10/2026', '24-10-2026'
    - Gazette textual format: '24th day of October, 2026' or '1st day of April, 2026'
    - Standard textual format: '24 October 2026', 'October 24, 2026'
    """
    if not date_str or not isinstance(date_str, str):
        return None

    clean = date_str.strip().strip(".,;")

    # 1. ISO format: YYYY-MM-DD
    iso_match = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", clean)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            pass

    # 2. DD/MM/YYYY or DD-MM-YYYY
    dm_match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", clean)
    if dm_match:
        try:
            return date(int(dm_match.group(3)), int(dm_match.group(2)), int(dm_match.group(1)))
        except ValueError:
            pass

    # 3. Gazette formal: "1st day of April, 2026" or "24th day of October, 2026"
    gazette_match = re.search(
        r"(\d{1,2})(?:st|nd|rd|th)?\s+day\s+of\s+([A-Za-z]+)[,\s]+(\d{4})",
        clean,
        re.IGNORECASE
    )
    if gazette_match:
        d = int(gazette_match.group(1))
        month_name = gazette_match.group(2).lower()
        y = int(gazette_match.group(3))
        m = _month_name_to_int(month_name)
        if m:
            try:
                return date(y, m, d)
            except ValueError:
                pass

    # 4. "24 October 2026" or "24th October 2026"
    textual_match = re.search(
        r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)[,\s]+(\d{4})",
        clean,
        re.IGNORECASE
    )
    if textual_match:
        d = int(textual_match.group(1))
        month_name = textual_match.group(2).lower()
        y = int(textual_match.group(3))
        m = _month_name_to_int(month_name)
        if m:
            try:
                return date(y, m, d)
            except ValueError:
                pass

    # 5. "October 24, 2026" or "October 24th, 2026"
    mdy_match = re.search(
        r"([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?[,\s]+(\d{4})",
        clean,
        re.IGNORECASE
    )
    if mdy_match:
        month_name = mdy_match.group(1).lower()
        d = int(mdy_match.group(2))
        y = int(mdy_match.group(3))
        m = _month_name_to_int(month_name)
        if m:
            try:
                return date(y, m, d)
            except ValueError:
                pass

    return None


def _month_name_to_int(month_str: str) -> Optional[int]:
    months = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }
    return months.get(month_str.lower().strip())


def sanitize_source_error(exc: Exception) -> Tuple[str, str]:
    """
    Sanitizes raw ingestion exceptions into customer-facing error categories and human-friendly messages.
    Guarantees no raw machine stack traces, database dumps, or local file paths leak to users.
    Returns: (error_category, clean_error_message)
    """
    if isinstance(exc, FileSizeExceededError):
        return ("PAYLOAD_OVERSIZED", "Document size exceeds the 25 MB safety limit.")
    if isinstance(exc, MalformedFileError):
        return ("MALFORMED_STREAM", "Source document stream is damaged or contains invalid binary headers.")
    if isinstance(exc, IngestionSecurityError):
        return ("SECURITY_BLOCKED", "Source document rejected by security boundary (SSRF or disallowed file type).")
    if isinstance(exc, TimeoutError) or "timeout" in str(exc).lower():
        return ("TIMEOUT", "Source portal request timed out after 30 seconds.")
    if isinstance(exc, (ConnectionError, socket.error)) or "connection" in str(exc).lower() or "unreachable" in str(exc).lower():
        return ("NETWORK_UNREACHABLE", "Portal network connection failed or server unreachable.")
    if isinstance(exc, SourceUnavailableError) or "503" in str(exc) or "throttle" in str(exc).lower() or "rate limit" in str(exc).lower():
        return ("SERVICE_THROTTLED", "Regulatory portal reported service unavailable (503) or rate-limit throttle.")
    if "extract" in str(exc).lower() or "parse" in str(exc).lower():
        return ("EXTRACTION_PARSE_ERROR", "Document text structure could not be parsed into recognized compliance parameters.")
    return ("INTERNAL_PROCESSING_ERROR", "An unexpected processing error occurred during automated ingestion.")

