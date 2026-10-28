"""
Plant Profile and Equipment Asset Models
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, Numeric, Date, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimestampedModel, utc_now


class PlantProfile(TimestampedModel):
    __tablename__ = "plant_profiles"
    
    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    industry_category: Mapped[str] = mapped_column(String(20), nullable=False, default="RED")  # RED, ORANGE, GREEN, WHITE
    sector: Mapped[str] = mapped_column(String(100), nullable=False, default="Chemicals")
    employee_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    contract_labour_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    built_up_area_sqm: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0, nullable=False)
    capital_investment_inr: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0, nullable=False)
    connected_power_kw: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    dg_set_capacity_kva: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    hazardous_waste_tpa: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    effluent_discharge_kld: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    boiler_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    steam_capacity_tph: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    raw_attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    
    # Relationships
    plant: Mapped["Plant"] = relationship("Plant", back_populates="profile")


class PlantEquipment(TimestampedModel):
    __tablename__ = "plant_equipment"
    
    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False, index=True)
    equipment_type: Mapped[str] = mapped_column(String(50), nullable=False)  # BOILER, PRESSURE_VESSEL, DG_SET, ETP, CHIMNEY
    tag_number: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity: Mapped[str] = mapped_column(String(100), nullable=False)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    installation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Relationships
    plant: Mapped["Plant"] = relationship("Plant", back_populates="equipment")
