"""
Pydantic Schemas for Human-Readable Admin Audit Logs
Never exposes raw machine JSON without readable descriptions and context.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AuditLogEntryResponse(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    readable_description: str
    changes_summary: List[str] = Field(default_factory=list)
    timestamp: datetime
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Dict[str, Any] = Field(default_factory=dict)


class PaginatedAuditLogsResponse(BaseModel):
    items: List[AuditLogEntryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    available_actions: List[str] = Field(default_factory=list)
    available_entity_types: List[str] = Field(default_factory=list)
