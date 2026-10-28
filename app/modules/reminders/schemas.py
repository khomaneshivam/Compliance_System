"""
Pydantic Schemas for Reminders, Notifications, and User Notification Preferences
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id: str
    plant_id: str
    notification_type: str  # DUE_SOON, OVERDUE, STATUS_CHANGE
    entity_type: str        # REQUIREMENT, TASK
    entity_id: str
    title: str
    message: str
    channel: str            # IN_APP, EMAIL
    status: str             # UNREAD, READ, DISMISSED
    sent_at: datetime
    read_at: Optional[datetime] = None
    metadata_payload: Dict[str, Any] = Field(default_factory=dict)


class PaginatedNotificationsResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    page: int
    page_size: int
    unread_count: int


class NotificationPreferenceResponse(BaseModel):
    email_enabled: bool
    in_app_enabled: bool
    lead_time_days: int
    notify_on_overdue: bool
    frequency: str


class NotificationPreferenceUpdateRequest(BaseModel):
    email_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    lead_time_days: Optional[int] = Field(None, ge=1, le=180)
    notify_on_overdue: Optional[bool] = None
    frequency: Optional[str] = Field(None, pattern="^(IMMEDIATE|DAILY_DIGEST)$")


class TriggerSchedulerResponse(BaseModel):
    scan_date: date
    scanned_tasks_count: int
    scanned_requirements_count: int
    generated_count: int
    deduplicated_count: int


class TestNotificationRequest(BaseModel):
    channel: str = Field("IN_APP", pattern="^(IN_APP|EMAIL)$")
    notification_type: str = Field("TEST", min_length=2, max_length=50)
    title: str = Field(..., min_length=3, max_length=255)
    message: str = Field(..., min_length=5, max_length=2000)
