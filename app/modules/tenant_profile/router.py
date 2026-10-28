"""
Plant & Company Profile Endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tenancy import User
from app.modules.identity_access.services import get_current_user, require_roles
from app.modules.tenant_profile.schemas import (
    PlantSummary,
    PlantProfileResponse,
    PlantProfileUpdate,
    PlantEquipmentResponse,
)
from app.modules.tenant_profile.services import (
    verify_plant_access,
    get_plants_for_user,
    get_or_create_plant_profile,
    update_plant_profile,
    get_plant_equipment,
)

router = APIRouter(prefix="/plants", tags=["Plants & Company Operational Profiles"])


@router.get("", response_model=List[PlantSummary])
def list_accessible_plants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists all manufacturing plants accessible to the authenticated user."""
    return get_plants_for_user(db, current_user)


@router.get("/{plant_id}", response_model=PlantSummary)
def get_plant_details(
    plant_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves metadata for a specific plant facility."""
    plant = verify_plant_access(db, plant_id, current_user)
    return plant


@router.get("/{plant_id}/profile", response_model=PlantProfileResponse)
def get_plant_operational_profile(
    plant_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves operational parameters used by the deterministic applicability engine."""
    plant = verify_plant_access(db, plant_id, current_user)
    profile = get_or_create_plant_profile(db, plant)
    return profile


@router.put(
    "/{plant_id}/profile",
    response_model=PlantProfileResponse,
    dependencies=[Depends(require_roles(["ADMIN", "PLANT_MANAGER"]))],
)
def update_plant_operational_profile(
    plant_id: str,
    profile_update: PlantProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates operational profile parameters (requires Admin or Plant Manager role)."""
    plant = verify_plant_access(db, plant_id, current_user)
    profile = update_plant_profile(db, plant, profile_update)
    return profile


@router.get("/{plant_id}/equipment", response_model=List[PlantEquipmentResponse])
def list_plant_equipment(
    plant_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists registered plant equipment (boilers, DG sets, pressure vessels, ETP)."""
    verify_plant_access(db, plant_id, current_user)
    return get_plant_equipment(db, plant_id)
