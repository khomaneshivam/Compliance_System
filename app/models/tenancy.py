"""
Tenancy, User, and Plant Entity Models
"""

from typing import Optional, List
from sqlalchemy import String, Boolean, ForeignKey, Index
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
