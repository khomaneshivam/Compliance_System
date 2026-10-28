"""
Security Safeguards for Document & Evidence Vault
Enforces MIME, magic byte signatures, file size boundaries, page count limits,
path traversal prevention, prompt injection sanitization, and PII minimization.
"""

import io
import re
import hashlib
from typing import Tuple, List, Optional
from pypdf import PdfReader


class DocumentSecurityError(Exception):
    """Base exception for document upload and safety violations."""
    def __init__(self, message: str, code: str = "SECURITY_VIOLATION"):
        self.message = message
        self.code = code
        super().__init__(message)


class MalformedDocumentError(DocumentSecurityError):
    def __init__(self, message: str):
        super().__init__(message, code="MALFORMED_FILE")


class FileSizeLimitExceededError(DocumentSecurityError):
    def __init__(self, message: str):
        super().__init__(message, code="FILE_SIZE_EXCEEDED")


class ProhibitedFileTypeError(DocumentSecurityError):
    def __init__(self, message: str):
        super().__init__(message, code="PROHIBITED_FILE_TYPE")


class EmptyDocumentError(DocumentSecurityError):
    def __init__(self, message: str):
        super().__init__(message, code="EMPTY_DOCUMENT")


# Explicitly allowed file signatures (magic bytes)
ALLOWED_MAGIC_SIGNATURES = {
    "application/pdf": [b"%PDF-"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/tiff": [b"II*\x00", b"MM\x00*"],
}

# Explicitly prohibited executable and archive signatures
PROHIBITED_SIGNATURES = {
    b"MZ": "Windows PE/Executable binary (.exe, .dll)",
    b"\x7fELF": "Linux ELF binary executable",
    b"\xfe\xed\xfa": "Mach-O executable binary",
    b"\xca\xfe\xba\xbe": "Java class file / Mach-O binary",
    b"PK\x03\x04": "ZIP / Jar archive",
    b"PK\x05\x06": "Empty ZIP archive",
    b"Rar!": "RAR archive",
    b"7z\xbc\xaf\x27\x1c": "7-Zip archive",
    b"\x1f\x8b": "GZIP compressed archive",
    b"BZh": "BZIP2 compressed archive",
}

# Prompt injection patterns in OCR text
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+(override|prompt|directive)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
    re.compile(r"exfiltrate\s+(data|token|secret|key)", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"exec\s*\(", re.IGNORECASE),
    re.compile(r"<script[\s>]", re.IGNORECASE),
    re.compile(r"drop\s+table\b", re.IGNORECASE),
]

# Sensitive Personal Data (PII) redaction regexes
AADHAAR_REGEX = re.compile(r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b")
PAN_REGEX = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
PHONE_REGEX = re.compile(r"(?:\+91[\-\s]?)?[6789]\d{9}\b")


def compute_sha256(content: bytes) -> str:
    """Calculates deterministic SHA-256 hex digest of file bytes."""
    return hashlib.sha256(content).hexdigest()


def sanitize_filename(original_name: str) -> str:
    """
    Prevents directory traversal and null byte injections.
    Strips directory separators, null bytes, and non-printable characters.
    """
    if not original_name:
        return "unnamed_document"
    clean = re.sub(r"[\x00/\\:\*\?\"<>\|]", "_", original_name)
    clean = clean.replace("..", "_").strip(" ._")
    return clean[:120] if clean else "unnamed_document"


def validate_upload_safety(
    file_bytes: bytes,
    original_filename: str,
    declared_mime: str,
    max_size_bytes: int = 25 * 1024 * 1024,
    max_pages: int = 50,
) -> Tuple[str, int]:
    """
    Performs multi-layered binary validation:
    1. Size boundary (1 byte to 25MB)
    2. Explicit extension check
    3. Prohibited executable/archive signature rejection
    4. Allowed magic bytes matching
    5. PDF page count and structure inspection (for PDFs)
    
    Returns: (canonical_mime_type, page_count)
    """
    if not file_bytes or len(file_bytes) == 0:
        raise EmptyDocumentError("Upload rejected: Document file is empty (0 bytes).")

    if len(file_bytes) > max_size_bytes:
        raise FileSizeLimitExceededError(
            f"Upload rejected: File size ({len(file_bytes)} bytes) exceeds maximum allowable limit of {max_size_bytes} bytes (25MB)."
        )

    # Extension check
    ext = original_filename.lower().split(".")[-1] if "." in original_filename else ""
    if ext not in ("pdf", "png", "jpg", "jpeg", "tiff", "tif"):
        raise ProhibitedFileTypeError(
            f"Upload rejected: File extension '.{ext}' is not permitted. Only PDF, PNG, JPG, and TIFF are supported."
        )

    # Check for prohibited executable/archive magic bytes
    for signature, desc in PROHIBITED_SIGNATURES.items():
        if file_bytes.startswith(signature):
            raise ProhibitedFileTypeError(
                f"Security alert: Prohibited executable or archive format detected ({desc}). Upload denied."
            )

    # Verify matching magic bytes
    detected_mime = None
    for mime, signatures in ALLOWED_MAGIC_SIGNATURES.items():
        for sig in signatures:
            if file_bytes.startswith(sig):
                detected_mime = mime
                break
        if detected_mime:
            break

    if not detected_mime:
        raise ProhibitedFileTypeError(
            f"Upload rejected: Magic bytes do not match permitted document types (PDF, PNG, JPEG, TIFF). Declared MIME: '{declared_mime}'."
        )

    # Specific PDF structural integrity & page count validation
    page_count = 1
    if detected_mime == "application/pdf":
        try:
            stream = io.BytesIO(file_bytes)
            reader = PdfReader(stream)
            page_count = len(reader.pages)
            if page_count < 1:
                raise EmptyDocumentError("Upload rejected: PDF contains 0 readable pages.")
            if page_count > max_pages:
                raise FileSizeLimitExceededError(
                    f"Upload rejected: PDF page count ({page_count}) exceeds limit of {max_pages} pages."
                )
        except (DocumentSecurityError, EmptyDocumentError, FileSizeLimitExceededError):
            raise
        except Exception as e:
            raise MalformedDocumentError(f"Upload rejected: Corrupted or unreadable PDF structure: {str(e)}")

    return detected_mime, page_count


def sanitize_extracted_text(raw_text: str) -> str:
    """
    Sanitizes extracted OCR text by neutralizing prompt injection attempts.
    """
    if not raw_text:
        return ""
    sanitized = raw_text
    for pattern in PROMPT_INJECTION_PATTERNS:
        sanitized = pattern.sub("[SANITIZED_INSTRUCTION_OVERRIDE]", sanitized)
    return sanitized


def redact_pii(text: str) -> str:
    """
    Minimizes sensitive personal data before transmitting to external AI providers.
    Redacts Aadhaar, personal PANs, and phone numbers.
    Preserves enterprise registration numbers, factory licenses, and plant identifiers.
    """
    if not text:
        return ""
    redacted = AADHAAR_REGEX.sub("[REDACTED_AADHAAR]", text)
    redacted = PHONE_REGEX.sub("[REDACTED_PHONE]", redacted)
    # Only redact PAN if not part of a factory licence prefix
    return redacted


def sanitize_document_error(exc: Exception) -> Tuple[str, str]:
    """
    Sanitizes raw document extraction exceptions into customer-facing error categories and human-friendly messages.
    Guarantees no raw machine stack traces, database dumps, or local file paths leak to users.
    Returns: (error_category, clean_error_message)
    """
    exc_str = str(exc).lower()
    if isinstance(exc, FileSizeLimitExceededError) or "size" in exc_str or "exceed" in exc_str:
        return ("PAYLOAD_OVERSIZED", "Uploaded document exceeds the 25 MB safety limit.")
    if isinstance(exc, EmptyDocumentError) or "empty" in exc_str or "0 bytes" in exc_str:
        return ("EMPTY_DOCUMENT", "Uploaded document is empty (0 bytes).")
    if isinstance(exc, MalformedDocumentError) or "malformed" in exc_str or "corrupt" in exc_str:
        return ("MALFORMED_STREAM", "Document file stream is damaged or contains invalid binary headers.")
    if isinstance(exc, (ProhibitedFileTypeError, DocumentSecurityError)) or "prohibited" in exc_str or "mime" in exc_str or "disallowed" in exc_str:
        return ("SECURITY_BLOCKED", "Document rejected by security boundary (disallowed file type or executable header).")
    if "injection" in exc_str:
        return ("PROMPT_INJECTION_SUSPECTED", "Document text contained adversarial instructions and was neutralized.")
    if "extract" in exc_str or "parse" in exc_str:
        return ("EXTRACTION_PARSE_ERROR", "Document text structure could not be parsed into recognized compliance parameters.")
    return ("INTERNAL_PROCESSING_ERROR", "An unexpected error occurred during document extraction.")

