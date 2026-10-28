"""
Abstract Base Provider Interfaces for Document OCR, Regulatory LLM, and Storage
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ExtractedFieldDTO(BaseModel):
    key: str
    value: str
    confidence_score: float  # 0.0 to 1.0
    confidence_band: str     # HIGH, MEDIUM, LOW
    bounding_box: Optional[Dict[str, float]] = None


class ValidationCheckDTO(BaseModel):
    check_code: str
    check_name: str
    status: str  # PASSED, FAILED, WARNING
    details: Optional[str] = None


class ParsedDocumentResult(BaseModel):
    document_type_detected: str
    fields: List[ExtractedFieldDTO]
    validation_checks: List[ValidationCheckDTO]
    raw_text: Optional[str] = None


class RegulatorySummaryResult(BaseModel):
    summary_plain_language: str
    key_changes: List[str]
    who_may_be_affected: List[str]
    candidate_impact_rating: str  # HIGH, MEDIUM, LOW


class DocumentParserProvider(ABC):
    """Abstract interface for Optical Character Recognition and layout analysis."""
    
    @abstractmethod
    def parse_document(self, file_bytes: bytes, filename: str) -> ParsedDocumentResult:
        """Parses document binary and extracts structured key-value pairs and validation results."""
        pass


class RegulatoryLLMProvider(ABC):
    """Abstract interface for legal text summarization and candidate impact generation."""
    
    @abstractmethod
    def summarize_notification(self, raw_text: str, authority: str, notification_ref: str) -> RegulatorySummaryResult:
        """Generates plain-language summary and candidate impact criteria."""
        pass


class StorageProvider(ABC):
    """Abstract interface for file persistence (Local filesystem or Cloud Object Store)."""
    
    @abstractmethod
    def save_file(self, content: bytes, destination_path: str) -> str:
        """Persists file content and returns the canonical path."""
        pass

    @abstractmethod
    def get_file(self, file_path: str) -> bytes:
        """Retrieves raw file bytes."""
        pass
