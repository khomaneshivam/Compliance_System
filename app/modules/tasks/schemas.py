"""
Pydantic Schemas for Compliance Remediation Tasks, Comments, and Attachments
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TaskCommentResponse(BaseModel):
    id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    comment_text: str
    created_at: datetime


class TaskAttachmentResponse(BaseModel):
    id: str
    document_id: Optional[str] = None
    filename: str
    file_size_bytes: int
    storage_key: Optional[str] = None
    uploaded_by_email: Optional[str] = None
    created_at: datetime


class TaskResponse(BaseModel):
    id: str
    plant_id: str
    plant_name: Optional[str] = None
    plant_requirement_id: Optional[str] = None
    requirement_code: Optional[str] = None
    requirement_title: Optional[str] = None
    title: str
    description: Optional[str] = None
    due_date: date
    priority: str  # HIGH, MEDIUM, LOW
    status: str    # TODO, IN_PROGRESS, BLOCKED, COMPLETED
    assigned_to_id: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_to_email: Optional[str] = None
    completed_at: Optional[datetime] = None
    blocked_reason: Optional[str] = None
    comments_count: int = 0
    attachments_count: int = 0
    created_at: datetime


class TaskDetailResponse(TaskResponse):
    comments: List[TaskCommentResponse] = Field(default_factory=list)
    attachments: List[TaskAttachmentResponse] = Field(default_factory=list)


class PaginatedTasksResponse(BaseModel):
    items: List[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TaskCreateRequest(BaseModel):
    plant_id: str
    plant_requirement_id: Optional[str] = None
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    due_date: date
    priority: str = Field("MEDIUM", pattern="^(HIGH|MEDIUM|LOW)$")
    assigned_to_user_id: Optional[str] = None


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    due_date: Optional[date] = None
    priority: Optional[str] = Field(None, pattern="^(HIGH|MEDIUM|LOW)$")
    assigned_to_user_id: Optional[str] = None


class TaskStatusTransitionRequest(BaseModel):
    new_status: str = Field(..., pattern="^(TODO|IN_PROGRESS|BLOCKED|COMPLETED)$")
    comment: Optional[str] = None


class TaskCommentCreateRequest(BaseModel):
    comment_text: str = Field(..., min_length=1, max_length=2000)


class TaskAttachmentLinkRequest(BaseModel):
    document_id: str
