"""
Plant & Company Profile Domain Services
"""

from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.tenancy import Plant, User
from app.models.profile import PlantProfile, PlantEquipment
from app.modules.tenant_profile.schemas import PlantProfileUpdate


def verify_plant_access(db: Session, plant_id: str, user: User) -> Plant:
    """Verifies that the target plant exists and belongs to the authenticated user's tenant."""
    plant = db.get(Plant, plant_id)
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Facility with ID '{plant_id}' not found."
        )
    if plant.tenant_id != user.tenant_id and user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have authorization to access this manufacturing facility."
        )
    return plant


def get_plants_for_user(db: Session, user: User) -> List[Plant]:
    """Retrieves all plants belonging to the user's tenant."""
    stmt = select(Plant).where(Plant.tenant_id == user.tenant_id).order_by(Plant.name)
    return list(db.scalars(stmt).all())


def get_or_create_plant_profile(db: Session, plant: Plant) -> PlantProfile:
    """Retrieves existing profile or initializes a default operational profile."""
    stmt = select(PlantProfile).where(PlantProfile.plant_id == plant.id)
    profile = db.scalars(stmt).first()
    if not profile:
        profile = PlantProfile(
            plant_id=plant.id,
            industry_category="RED",
            sector="Chemicals",
            employee_count=120,
            contract_labour_count=45,
            built_up_area_sqm=12500.0,
            capital_investment_inr=85000000.0,
            connected_power_kw=750.0,
            dg_set_capacity_kva=500.0,
            hazardous_waste_tpa=12.5,
            effluent_discharge_kld=45.0,
            boiler_count=1,
            steam_capacity_tph=4.5,
            raw_attributes={}
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def update_plant_profile(
    db: Session,
    plant: Plant,
    profile_update: PlantProfileUpdate
) -> PlantProfile:
    """Updates operational profile fields."""
    profile = get_or_create_plant_profile(db, plant)
    update_data = profile_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(profile, key, value)
        
    db.commit()
    db.refresh(profile)
    return profile


def get_plant_equipment(db: Session, plant_id: str) -> List[PlantEquipment]:
    """Lists registered equipment assets for a facility."""
    stmt = select(PlantEquipment).where(PlantEquipment.plant_id == plant_id).order_by(PlantEquipment.equipment_type)
    return list(db.scalars(stmt).all())
