"""
Reminder & Alert Notification Router (/api/v1/reminders)
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.tenancy import User
from app.modules.reminders.schemas import (
    NotificationResponse,
    PaginatedNotificationsResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    TriggerSchedulerResponse,
    TestNotificationRequest,
)
from app.modules.reminders.services import reminder_service

reminders_router = APIRouter(prefix="/reminders", tags=["Reminders & Notifications"])


@reminders_router.get("/notifications", response_model=PaginatedNotificationsResponse, summary="List Notifications")
def list_notifications_endpoint(
    status: Optional[str] = Query("ALL", description="ALL, UNREAD, READ, DISMISSED"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns paginated in-app notifications and reminders for the current user and facility.
    """
    return reminder_service.list_notifications(
        db=db, user=current_user, status=status, page=page, page_size=page_size
    )


@reminders_router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse, summary="Mark Notification Read")
def mark_notification_read_endpoint(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Marks a single notification as read.
    """
    return reminder_service.mark_as_read(db=db, user=current_user, notification_id=notification_id)


@reminders_router.post("/notifications/read-all", summary="Mark All Read")
def mark_all_notifications_read_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Marks all notifications for current user as read.
    """
    count = reminder_service.mark_all_as_read(db=db, user=current_user)
    return {"message": f"Marked {count} notifications as read", "count": count}


@reminders_router.post("/run-scheduler", response_model=TriggerSchedulerResponse, summary="Trigger Reminder Scan")
def run_reminder_scheduler_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Triggers an on-demand scheduler scan for due-soon and overdue tasks and requirements with deduplication.
    """
    return reminder_service.run_reminder_scan(db=db, tenant_id=current_user.tenant_id)


@reminders_router.get("/preferences", response_model=NotificationPreferenceResponse, summary="Get Notification Preferences")
def get_preferences_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns user notification preferences (lead time, channels, overdue alerts).
    """
    pref = reminder_service.get_or_create_preferences(db=db, user=current_user)
    return NotificationPreferenceResponse(
        email_enabled=pref.email_enabled,
        in_app_enabled=pref.in_app_enabled,
        lead_time_days=pref.lead_time_days,
        notify_on_overdue=pref.notify_on_overdue,
        frequency=pref.frequency,
    )


@reminders_router.put("/preferences", response_model=NotificationPreferenceResponse, summary="Update Notification Preferences")
def update_preferences_endpoint(
    payload: NotificationPreferenceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates user notification preferences.
    """
    return reminder_service.update_preferences(db=db, user=current_user, payload=payload)


@reminders_router.post("/test-notification", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED, summary="Send Test Notification")
def send_test_notification_endpoint(
    payload: TestNotificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dispatches a test notification through the test adapter for verification and auditing.
    """
    return reminder_service.send_test_notification(db=db, user=current_user, payload=payload)
