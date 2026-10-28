"""
Core Dependency Injection & Tenant Isolation Providers
"""

from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import TenantAccessDeniedError, EntityNotFoundError, InsufficientPermissionsError
from app.core.logging import set_tenant_context
from app.models.tenancy import User, Plant
from app.modules.identity_access.services import get_current_user, require_roles


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Verifies that the current user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact your compliance administrator."
        )
    # Set contextvar for structured logging
    set_tenant_context(current_user.tenant_id)
    return current_user


def get_current_tenant_id(current_user: User = Depends(get_current_active_user)) -> str:
    """Provides current authenticated tenant ID for scoping queries."""
    return current_user.tenant_id


def verify_plant_tenant_access(
    plant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Plant:
    """
    Enforces strict server-side tenant isolation for plant facilities.
    Prevents cross-tenant data access, inference, or modification.
    """
    plant = db.get(Plant, plant_id)
    if not plant:
        raise EntityNotFoundError("Facility", plant_id)
    if plant.tenant_id != current_user.tenant_id and current_user.role != "SUPER_ADMIN":
        raise TenantAccessDeniedError(
            f"Access denied: plant '{plant_id}' belongs to another organization."
        )
    return plant
