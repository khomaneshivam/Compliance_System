"""
Abstract Source Adapter Interface & Fetched Document Contracts
"""

from abc import ABC, abstractmethod
import hashlib
from datetime import date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FetchedRegulatoryPayload(BaseModel):
    """Normalized payload delivered by a source adapter."""
    external_id: str = Field(..., description="Unique notification/circular identifier (e.g. S.O. 1234(E))")
    title: str = Field(..., description="Official title of the regulatory update")
    document_url: str = Field(..., description="Canonical source download URL")
    published_date: Optional[date] = Field(None, description="Official publication date")
    effective_date: Optional[date] = Field(None, description="Date notification comes into legal force")
    raw_bytes: bytes = Field(..., description="Raw binary content of the fetched document")
    mime_type: str = Field("application/pdf", description="MIME content type")
    content_hash: str = Field("", description="SHA-256 fingerprint of raw_bytes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional provenance metadata")

    def model_post_init(self, __context: Any) -> None:
        if not self.content_hash and self.raw_bytes:
            self.content_hash = hashlib.sha256(self.raw_bytes).hexdigest()


class BaseSourceAdapter(ABC):
    """Abstract interface that all official and fixture adapters must implement."""

    def __init__(self, source_code: str, base_url: str, rate_limit_per_minute: int = 12):
        self.source_code = source_code
        self.base_url = base_url
        self.rate_limit_per_minute = rate_limit_per_minute

    @abstractmethod
    def poll(self) -> List[FetchedRegulatoryPayload]:
        """
        Polls the source for newly published circulars, gazettes, or notifications.
        Returns a list of fetched payloads with hashes and metadata.
        """
        pass
