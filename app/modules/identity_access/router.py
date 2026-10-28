"""
Authentication & User Endpoints
"""

from datetime import timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.core.rate_limit import rate_limit
from app.models.tenancy import User
from app.modules.identity_access.schemas import (
    LoginRequest,
    TokenResponse,
    UserSummary,
    UserInviteRequest,
    UserListItem,
)
from app.modules.identity_access.services import (
    authenticate_user,
    get_current_user,
    require_roles,
    build_user_summary,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit(max_requests=15, window_seconds=60, key_prefix="login"))],
)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates user credentials and returns a signed JWT token."""
    user = authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password. Please verify your credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id,
        claims={"tenant_id": user.tenant_id, "role": user.role},
        expires_delta=access_token_expires,
    )
    
    user_summary = build_user_summary(db, user)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_summary,
    )


@router.get("/me", response_model=UserSummary)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves current user profile and accessible plant scopes."""
    return build_user_summary(db, current_user)


@router.get("/users", response_model=List[UserListItem])
def list_tenant_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists enterprise team members belonging to the current tenant."""
    users = db.query(User).filter(User.tenant_id == current_user.tenant_id).all()
    result = []
    for u in users:
        summary = build_user_summary(db, u)
        result.append(
            UserListItem(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                tenant_id=u.tenant_id,
                tenant_name=summary.tenant_name,
                plant_ids=summary.plant_ids,
                is_active=u.is_active,
                created_at=u.created_at.isoformat() if u.created_at else "",
            )
        )
    return result


@router.post("/users/invite", response_model=UserListItem)
def invite_user(
    invite_data: UserInviteRequest,
    current_user: User = Depends(require_roles(["ADMIN", "SUPER_ADMIN"])),
    db: Session = Depends(get_db),
):
    """Provisions a new enterprise team member with role-based access."""
    from app.core.security import get_password_hash
    import uuid

    # Prevent privilege escalation: only SUPER_ADMIN can invite a SUPER_ADMIN
    if invite_data.role == "SUPER_ADMIN" and current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilege escalation prohibited: Only Super Administrators can provision another Super Administrator.",
        )

    existing = db.query(User).filter(User.email == invite_data.email.lower().strip()).first()
    if existing:
        if existing.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email address is already registered under another organization.",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address is already registered in your organization.",
        )

    new_user = User(
        id=f"user-{uuid.uuid4().hex[:8]}",
        tenant_id=current_user.tenant_id,
        email=invite_data.email,
        full_name=invite_data.full_name,
        hashed_password=get_password_hash("Password123!"),
        role=invite_data.role,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    summary = build_user_summary(db, new_user)
    return UserListItem(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        tenant_id=new_user.tenant_id,
        tenant_name=summary.tenant_name,
        plant_ids=summary.plant_ids,
        is_active=new_user.is_active,
        created_at=new_user.created_at.isoformat() if new_user.created_at else "",
    )

