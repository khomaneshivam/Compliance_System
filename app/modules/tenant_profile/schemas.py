"""
Plant & Company Profile Pydantic Schemas
"""

from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PlantSummary(BaseModel):
    id: str
    name: str
    code: str
    jurisdiction: str
    district: str
    pincode: str

    model_config = {"from_attributes": True}


class PlantProfileResponse(BaseModel):
    id: str
    plant_id: str
    industry_category: Optional[str] = None
    sector: Optional[str] = None
    employee_count: Optional[int] = None
    contract_labour_count: Optional[int] = None
    built_up_area_sqm: Optional[float] = None
    capital_investment_inr: Optional[float] = None
    connected_power_kw: Optional[float] = None
    dg_set_capacity_kva: Optional[float] = None
    hazardous_waste_tpa: Optional[float] = None
    effluent_discharge_kld: Optional[float] = None
    boiler_count: Optional[int] = None
    steam_capacity_tph: Optional[float] = None
    raw_attributes: Dict[str, Any] = {}
    profile_status: str
    verified_by_user_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None

    model_config = {"from_attributes": True}


class PlantProfileUpdate(BaseModel):
    industry_category: Optional[str] = None
    sector: Optional[str] = None
    employee_count: Optional[int] = Field(None, ge=0)
    contract_labour_count: Optional[int] = Field(None, ge=0)
    built_up_area_sqm: Optional[float] = Field(None, ge=0)
    capital_investment_inr: Optional[float] = Field(None, ge=0)
    connected_power_kw: Optional[float] = Field(None, ge=0)
    dg_set_capacity_kva: Optional[float] = Field(None, ge=0)
    hazardous_waste_tpa: Optional[float] = Field(None, ge=0)
    effluent_discharge_kld: Optional[float] = Field(None, ge=0)
    boiler_count: Optional[int] = Field(None, ge=0)
    steam_capacity_tph: Optional[float] = Field(None, ge=0)
    raw_attributes: Optional[Dict[str, Any]] = None


class ProfileVerificationRequest(BaseModel):
    verification_notes: Optional[str] = Field(None, max_length=2000)


class PlantEquipmentResponse(BaseModel):
    id: str
    plant_id: str
    equipment_type: str
    tag_number: str
    capacity: Optional[str] = None
    manufacturer: Optional[str] = None
    installation_date: Optional[date] = None

    model_config = {"from_attributes": True}
