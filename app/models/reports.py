"""
Readiness and Evidence Report Job Models
"""

from datetime import datetime, date
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel, utc_now


class ReadinessReportJob(TimestampedModel):
    __tablename__ = "readiness_report_jobs"

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    report_title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="QUEUED", index=True)  # QUEUED, GENERATING, COMPLETED, FAILED
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_range_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_range_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    prepared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    data_as_of: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    file_format: Mapped[str] = mapped_column(String(10), nullable=False, default="JSON")  # JSON, HTML, PDF
    storage_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary_metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    report_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    plant: Mapped["Plant"] = relationship("Plant")
    requested_by: Mapped[Optional["User"]] = relationship("User")
