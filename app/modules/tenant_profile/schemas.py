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
    industry_category: str
    sector: str
    employee_count: int
    contract_labour_count: int
    built_up_area_sqm: float
    capital_investment_inr: float
    connected_power_kw: float
    dg_set_capacity_kva: float
    hazardous_waste_tpa: float
    effluent_discharge_kld: float
    boiler_count: int
    steam_capacity_tph: float
    raw_attributes: Dict[str, Any] = {}

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


class PlantEquipmentResponse(BaseModel):
    id: str
    plant_id: str
    equipment_type: str
    tag_number: str
    capacity: str
    manufacturer: Optional[str] = None
    installation_date: Optional[date] = None

    model_config = {"from_attributes": True}
