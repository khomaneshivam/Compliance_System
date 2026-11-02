"""
Plant & Company Profile Domain Services
"""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.tenancy import Plant, User
from app.models.profile import PlantProfile, PlantEquipment
from app.core.config import settings
from app.core.exceptions import ConflictError
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
    """Retrieves a profile or creates an explicitly incomplete, unknown-valued record."""
    stmt = select(PlantProfile).where(PlantProfile.plant_id == plant.id)
    profile = db.scalars(stmt).first()
    if not profile:
        profile = PlantProfile(
            plant_id=plant.id,
            profile_status="INCOMPLETE",
            raw_attributes={},
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def update_plant_profile(
    db: Session,
    plant: Plant,
    profile_update: PlantProfileUpdate,
    user: User,
) -> PlantProfile:
    """Updates profile fields and invalidates any previous human verification."""
    profile = get_or_create_plant_profile(db, plant)
    update_data = profile_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(profile, key, value)

    # Preserve DEMO_FIXTURE only under automated test execution. Real updates
    # invalidate prior verification and must be reviewed by another user.
    if not (settings.ENVIRONMENT == "test" and profile.profile_status == "DEMO_FIXTURE"):
        profile.profile_status = "INCOMPLETE"
        profile.verified_by_user_id = None
        profile.verified_at = None
        profile.verification_notes = None
    profile.updated_by_user_id = user.id

    db.commit()
    db.refresh(profile)
    return profile


def verify_plant_profile(
    db: Session,
    plant: Plant,
    user: User,
    verification_notes: Optional[str] = None,
) -> PlantProfile:
    """Verify a completed facility profile; enforces maker-checker separation."""
    profile = get_or_create_plant_profile(db, plant)
    if profile.updated_by_user_id and profile.updated_by_user_id == user.id:
        raise ConflictError(
            "The user who last edited this profile cannot verify the same revision. "
            "A different authorized reviewer must approve it."
        )
    if profile.profile_status == "VERIFIED":
        raise ConflictError("This plant profile is already verified. Make a new revision before re-verification.")

    profile.profile_status = "VERIFIED"
    profile.verified_by_user_id = user.id
    profile.verified_at = datetime.now(timezone.utc)
    profile.verification_notes = verification_notes
    db.commit()
    db.refresh(profile)
    return profile


def get_plant_equipment(db: Session, plant_id: str) -> List[PlantEquipment]:
    """Lists registered equipment assets for a facility."""
    stmt = select(PlantEquipment).where(PlantEquipment.plant_id == plant_id).order_by(PlantEquipment.equipment_type)
    return list(db.scalars(stmt).all())
