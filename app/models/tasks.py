"""
Compliance Remediation Task and Audit Log Models
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Date, DateTime, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel


class ComplianceTask(TimestampedModel):
    __tablename__ = "compliance_tasks"
    
    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    plant_requirement_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("plant_requirements.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")  # HIGH, MEDIUM, LOW
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="TODO", index=True)  # TODO, IN_PROGRESS, BLOCKED, COMPLETED
    assigned_to_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    plant: Mapped["Plant"] = relationship("Plant")
    requirement: Mapped[Optional["PlantRequirement"]] = relationship("PlantRequirement")
    assignee: Mapped[Optional["User"]] = relationship("User")
    comments: Mapped[List["TaskComment"]] = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan", order_by="TaskComment.created_at.asc()")
    attachments: Mapped[List["TaskAttachment"]] = relationship("TaskAttachment", back_populates="task", cascade="all, delete-orphan", order_by="TaskAttachment.created_at.asc()")


class TaskComment(TimestampedModel):
    __tablename__ = "task_comments"

    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("compliance_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    task: Mapped["ComplianceTask"] = relationship("ComplianceTask", back_populates="comments")
    user: Mapped[Optional["User"]] = relationship("User")


class TaskAttachment(TimestampedModel):
    __tablename__ = "task_attachments"

    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("compliance_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("compliance_documents.id", ondelete="SET NULL"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    uploaded_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    task: Mapped["ComplianceTask"] = relationship("ComplianceTask", back_populates="attachments")
    document: Mapped[Optional["ComplianceDocument"]] = relationship("ComplianceDocument")
    uploaded_by: Mapped[Optional["User"]] = relationship("User")


class AuditLog(TimestampedModel):
    __tablename__ = "audit_logs"
    
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    previous_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    new_state: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    user: Mapped[Optional["User"]] = relationship("User")
