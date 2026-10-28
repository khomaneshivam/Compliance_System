"""
Structured Logging & Correlation ID Module
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.core.config import settings

# Thread-safe context variable for request correlation ID
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")
tenant_id_ctx: ContextVar[str] = ContextVar("tenant_id", default="")


def get_correlation_id() -> str:
    """Retrieves current correlation ID or generates a new one if unset."""
    cid = correlation_id_ctx.get()
    if not cid:
        cid = str(uuid.uuid4())
        correlation_id_ctx.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Sets the correlation ID for the active request context."""
    correlation_id_ctx.set(cid)


def set_tenant_context(tenant_id: str) -> None:
    """Sets the active tenant ID for the request context."""
    tenant_id_ctx.set(tenant_id)


import re

SENSITIVE_KEY_NAMES = {
    "password", "secret", "token", "authorization", "api_key",
    "access_token", "refresh_token", "private_key", "client_secret",
}

JWT_PATTERN = re.compile(r"eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]+")
BEARER_PATTERN = re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{15,}")
AADHAAR_PATTERN = re.compile(r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b")


def sanitize_log_text(text: str) -> str:
    """Masks inline JWTs, Bearer tokens, and sensitive numbers in log messages."""
    if not isinstance(text, str):
        return text
    sanitized = JWT_PATTERN.sub("[REDACTED_JWT]", text)
    sanitized = BEARER_PATTERN.sub("Bearer [REDACTED_TOKEN]", sanitized)
    sanitized = AADHAAR_PATTERN.sub("[REDACTED_AADHAAR]", sanitized)
    return sanitized


def sanitize_log_data(data: Any) -> Any:
    """Recursively redacts sensitive keys and values from logging dictionaries/lists."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if any(sensitive in str(k).lower() for sensitive in SENSITIVE_KEY_NAMES):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_log_data(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_log_data(item) for item in data]
    elif isinstance(data, str):
        return sanitize_log_text(data)
    return data


redact_sensitive_data = sanitize_log_data


class JSONFormatter(logging.Formatter):
    """Formats log records into single-line JSON objects with automated secret redaction."""

    def format(self, record: logging.LogRecord) -> str:
        raw_msg = record.getMessage()
        sanitized_msg = sanitize_log_text(raw_msg)

        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitized_msg,
            "correlation_id": correlation_id_ctx.get() or None,
            "tenant_id": tenant_id_ctx.get() or None,
        }
        
        # Attach exception info if present
        if record.exc_info:
            raw_exc = self.formatException(record.exc_info)
            log_payload["exception"] = sanitize_log_text(raw_exc)
            
        # Attach any extra attributes provided in extra={} with recursive redaction
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_payload["data"] = sanitize_log_data(record.extra_data)

        return json.dumps(log_payload, default=str)


def setup_logging() -> None:
    """Configures root logger based on application settings."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if settings.LOG_FORMAT.lower() == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        )
        
    root_logger.addHandler(console_handler)
    
    # Suppress overly chatty third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


logger = logging.getLogger("plantproof")
