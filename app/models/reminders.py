"""
Reminder and Notification Models for Compliance Tasks & Expiring Obligations
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel, utc_now


class ReminderNotification(TimestampedModel):
    __tablename__ = "reminder_notifications"

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # DUE_SOON, OVERDUE, STATUS_CHANGE
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # REQUIREMENT, TASK
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_APP")  # IN_APP, EMAIL
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNREAD", index=True)  # UNREAD, READ, DISMISSED
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dedup_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    metadata_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    plant: Mapped["Plant"] = relationship("Plant")
    user: Mapped[Optional["User"]] = relationship("User")

    __table_args__ = (
        UniqueConstraint("dedup_key", name="uq_reminder_dedup_key"),
    )


class UserNotificationPreference(TimestampedModel):
    __tablename__ = "user_notification_preferences"

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    notify_on_overdue: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), default="IMMEDIATE", nullable=False)  # IMMEDIATE, DAILY_DIGEST

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    user: Mapped["User"] = relationship("User")
