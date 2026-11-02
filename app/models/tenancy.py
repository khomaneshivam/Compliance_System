"""
Tenancy, User, and Plant Entity Models
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, ForeignKey, Index, DateTime, Integer, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel


class Tenant(TimestampedModel):
    __tablename__ = "tenants"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    plants: Mapped[List["Plant"]] = relationship("Plant", back_populates="tenant", cascade="all, delete-orphan")


class User(TimestampedModel):
    __tablename__ = "users"
    
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="VIEWER")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")


class UserInvitation(TimestampedModel):
    """Single-use, expiring user invitation. Only a token hash is persisted."""

    __tablename__ = "user_invitations"

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", server_default="PENDING")
    delivery_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", server_default="PENDING"
    )
    invited_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    accepted_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_error_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    resend_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED', 'REVOKED', 'EXPIRED')",
            name="ck_user_invitations_status",
        ),
        CheckConstraint(
            "delivery_status IN ('PENDING', 'SENT', 'FAILED')",
            name="ck_user_invitations_delivery_status",
        ),
        Index(
            "uq_user_invitations_pending_tenant_email",
            "tenant_id",
            "email",
            unique=True,
            sqlite_where=(status == "PENDING"),
            postgresql_where=(status == "PENDING"),
        ),
    )


class Plant(TimestampedModel):
    __tablename__ = "plants"
    
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False, default="Maharashtra")
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="plants")
    profile: Mapped[Optional["PlantProfile"]] = relationship("PlantProfile", back_populates="plant", uselist=False, cascade="all, delete-orphan")
    equipment: Mapped[List["PlantEquipment"]] = relationship("PlantEquipment", back_populates="plant", cascade="all, delete-orphan")
    requirements: Mapped[List["PlantRequirement"]] = relationship("PlantRequirement", back_populates="plant", cascade="all, delete-orphan")
