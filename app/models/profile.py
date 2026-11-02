"""
Plant Profile and Equipment Asset Models
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, Numeric, Float, Date, DateTime, ForeignKey, JSON, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel, utc_now


class PlantProfile(TimestampedModel):
    __tablename__ = "plant_profiles"

    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Null means unknown. Do not substitute zero/default classifications.
    industry_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    employee_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    contract_labour_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    built_up_area_sqm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    capital_investment_inr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    connected_power_kw: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dg_set_capacity_kva: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hazardous_waste_tpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    effluent_discharge_kld: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    boiler_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    steam_capacity_tph: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    profile_status: Mapped[str] = mapped_column(
        String(20), default="INCOMPLETE", server_default="INCOMPLETE", nullable=False
    )  # INCOMPLETE, VERIFIED, DEMO_FIXTURE
    updated_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    verified_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "profile_status IN ('INCOMPLETE', 'VERIFIED', 'DEMO_FIXTURE')",
            name="ck_plant_profiles_status",
        ),
    )
    
    # Relationships
    plant: Mapped["Plant"] = relationship("Plant", back_populates="profile")


class PlantEquipment(TimestampedModel):
    __tablename__ = "plant_equipment"

    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    equipment_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Normalized asset identifier; legacy identifier remains stored separately.
    tag_number: Mapped[str] = mapped_column(String(100), nullable=False)
    identifier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Human-readable capacity is used by current UI/API. Original numeric
    # capacity and unit remain available for calculations and historical fidelity.
    capacity: Mapped[Optional[str]] = mapped_column("capacity_display", String(100), nullable=True)
    capacity_numeric: Mapped[Optional[float]] = mapped_column("capacity", Float, nullable=True)
    capacity_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    operating_parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    manufacturer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    installation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Relationships
    plant: Mapped["Plant"] = relationship("Plant", back_populates="equipment")
