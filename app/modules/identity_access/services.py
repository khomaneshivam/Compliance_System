"""
Identity & Access Domain Services and Authentication Dependencies
"""

from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, decode_access_token
from app.models.tenancy import User, Tenant, Plant
from app.modules.identity_access.schemas import UserSummary

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Finds a user by email address."""
    stmt = select(User).where(User.email == email.lower().strip())
    return db.scalars(stmt).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Validates user credentials."""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI dependency to extract and authenticate current active user from JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or session has expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
        
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
        
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception
        
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def build_user_summary(db: Session, user: User) -> UserSummary:
    """Builds a UserSummary DTO including tenant name and accessible plants."""
    tenant = db.get(Tenant, user.tenant_id)
    tenant_name = tenant.name if tenant else None
    
    # In initial multi-tenant model, users have access to all plants belonging to their tenant
    plants_stmt = select(Plant.id).where(Plant.tenant_id == user.tenant_id)
    plant_ids = list(db.scalars(plants_stmt).all())
    
    return UserSummary(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        tenant_id=user.tenant_id,
        tenant_name=tenant_name,
        plant_ids=plant_ids
    )


def require_roles(allowed_roles: List[str]):
    """Role-Based Access Control dependency factory."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles and current_user.role != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' is not authorized to perform this action."
            )
        return current_user
    return role_checker
