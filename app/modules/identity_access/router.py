"""
Authentication & User Endpoints
"""

from datetime import datetime, timedelta, timezone
from typing import List
import hashlib
import secrets
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash
from app.core.rate_limit import rate_limit
from app.models.tenancy import User, UserInvitation, UserPasswordResetToken
from app.modules.identity_access.schemas import (
    LoginRequest,
    TokenResponse,
    UserSummary,
    UserInviteRequest,
    UserListItem,
    InvitationCreatedResponse,
    AcceptInvitationRequest,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    PasswordResetCompleteRequest,
)
from app.modules.identity_access.services import (
    authenticate_user,
    get_current_user,
    require_roles,
    build_user_summary,
)
from app.modules.reminders.services import get_notification_adapter

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
        claims={"tenant_id": user.tenant_id, "role": user.role, "auth_version": user.auth_version},
        expires_delta=access_token_expires,
    )
    
    user_summary = build_user_summary(db, user)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_summary,
    )


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=300, key_prefix="password_reset_request"))],
)
def request_password_reset(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """Starts a password reset without disclosing whether an email address exists."""
    from sqlalchemy import func, select

    generic_message = (
        "If an active account exists for this email address, password reset instructions will be sent."
    )
    normalized_email = str(request.email).strip().lower()
    user = db.scalar(
        select(User).where(func.lower(User.email) == normalized_email, User.is_active.is_(True))
    )
    if not user:
        return PasswordResetRequestResponse(message=generic_message)

    now = datetime.now(timezone.utc)
    prior_requests = list(
        db.scalars(
            select(UserPasswordResetToken).where(
                UserPasswordResetToken.user_id == user.id,
                UserPasswordResetToken.status == "PENDING",
            )
        ).all()
    )
    for prior in prior_requests:
        prior.status = "REVOKED"
        prior.revoked_at = now
    db.flush()

    raw_token = secrets.token_urlsafe(48)
    reset_record = UserPasswordResetToken(
        user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        status="PENDING",
        delivery_status="PENDING",
        requested_at=now,
        expires_at=now + timedelta(hours=1),
    )
    db.add(reset_record)
    db.commit()
    db.refresh(reset_record)

    reset_url = f"{settings.PUBLIC_APP_URL.rstrip('/')}/reset-password#token={quote(raw_token)}"
    email_body = (
        f"Hello {user.full_name},\n\n"
        "A password reset was requested for your PlantProof account.\n"
        f"Use this one-time link to create a new password:\n{reset_url}\n\n"
        f"This link expires at {reset_record.expires_at.isoformat()} (one hour). "
        "If you did not request this, ignore this email.\n"
    )
    adapter = get_notification_adapter(mode=settings.NOTIFICATION_DELIVERY_MODE)
    delivered = adapter.send(
        recipient=user.email,
        title="Reset your PlantProof password",
        message=email_body,
        channel="EMAIL",
        metadata={"password_reset_id": reset_record.id},
    )

    if delivered is False:
        reset_record.status = "REVOKED"
        reset_record.delivery_status = "FAILED"
        reset_record.delivery_error_code = "EMAIL_DELIVERY_FAILED"
        reset_record.revoked_at = datetime.now(timezone.utc)
        db.commit()
        # Keep response generic to avoid exposing account state or mail-provider results.
        return PasswordResetRequestResponse(message=generic_message)

    reset_record.delivery_status = "SENT"
    reset_record.delivered_at = datetime.now(timezone.utc)
    db.commit()

    return PasswordResetRequestResponse(
        message=generic_message,
        debug_token=raw_token if settings.ENVIRONMENT in ("development", "test") else None,
    )


@router.post(
    "/password-reset/complete",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=300, key_prefix="password_reset_complete"))],
)
def complete_password_reset(
    request: PasswordResetCompleteRequest,
    db: Session = Depends(get_db),
):
    """Redeems a single-use reset token, changes the password and invalidates old JWTs."""
    from sqlalchemy import select

    token_hash = hashlib.sha256(request.token.encode("utf-8")).hexdigest()
    reset_record = db.scalar(
        select(UserPasswordResetToken)
        .where(UserPasswordResetToken.token_hash == token_hash)
        .with_for_update()
    )
    now = datetime.now(timezone.utc)

    if not reset_record or reset_record.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This password reset link is invalid, expired or already used.",
        )
    if reset_record.expires_at <= now:
        reset_record.status = "EXPIRED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This password reset link is invalid, expired or already used.",
        )

    user = db.get(User, reset_record.user_id)
    if not user or not user.is_active:
        reset_record.status = "REVOKED"
        reset_record.revoked_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This password reset link is invalid, expired or already used.",
        )

    user.hashed_password = get_password_hash(request.new_password)
    user.auth_version += 1
    reset_record.status = "USED"
    reset_record.used_at = now

    # Invalidate any other reset links issued for the same account.
    other_requests = list(
        db.scalars(
            select(UserPasswordResetToken).where(
                UserPasswordResetToken.user_id == user.id,
                UserPasswordResetToken.id != reset_record.id,
                UserPasswordResetToken.status == "PENDING",
            )
        ).all()
    )
    for other in other_requests:
        other.status = "REVOKED"
        other.revoked_at = now

    db.commit()
    return {"message": "Password updated. Sign in again with your new password."}


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


@router.post(
    "/users/invite",
    response_model=InvitationCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60, key_prefix="user_invite"))],
)
def invite_user(
    invite_data: UserInviteRequest,
    current_user: User = Depends(require_roles(["ADMIN", "SUPER_ADMIN"])),
    db: Session = Depends(get_db),
):
    """Creates a pending single-use invitation; accounts activate only after the invitee sets a password."""
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError

    allowed_roles = {"ADMIN", "PLANT_MANAGER", "EHS_MANAGER", "VIEWER", "AUDITOR", "SUPER_ADMIN"}
    requested_role = invite_data.role.strip().upper()
    if requested_role not in allowed_roles:
        raise HTTPException(status_code=422, detail="The requested role is not supported.")
    if requested_role == "SUPER_ADMIN" and current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a Super Administrator can invite another Super Administrator.",
        )
    if invite_data.plant_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Plant-scoped grants are not yet supported by this invitation endpoint. Invite without plant_ids.",
        )

    normalized_email = str(invite_data.email).strip().lower()
    if not invite_data.full_name.strip():
        raise HTTPException(status_code=422, detail="Full name is required.")

    existing_user = db.scalar(select(User).where(User.email == normalized_email))
    if existing_user:
        if existing_user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email address is already registered under another organization.",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address is already registered in your organization.",
        )

    now = datetime.now(timezone.utc)
    existing_invitation = db.scalar(
        select(UserInvitation).where(
            UserInvitation.tenant_id == current_user.tenant_id,
            UserInvitation.email == normalized_email,
            UserInvitation.status == "PENDING",
        )
    )
    if existing_invitation and existing_invitation.expires_at <= now:
        existing_invitation.status = "EXPIRED"
        existing_invitation.revoked_at = now
        db.flush()
        existing_invitation = None
    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invitation already exists for this email address.",
        )

    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    invitation = UserInvitation(
        tenant_id=current_user.tenant_id,
        email=normalized_email,
        full_name=invite_data.full_name.strip(),
        role=requested_role,
        token_hash=token_hash,
        status="PENDING",
        delivery_status="PENDING",
        invited_by_user_id=current_user.id,
        expires_at=now + timedelta(hours=24),
    )
    db.add(invitation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invitation already exists for this email address.",
        )
    db.refresh(invitation)

    invitation_url = (
        f"{settings.PUBLIC_APP_URL.rstrip('/')}/accept-invitation#token={quote(raw_token)}"
    )
    email_body = (
        f"Hello {invitation.full_name},\n\n"
        f"You have been invited to join PlantProof as {invitation.role}.\n"
        f"Use this one-time link to create your password and activate your account:\n"
        f"{invitation_url}\n\n"
        f"This invitation expires at {invitation.expires_at.isoformat()} (24 hours). "
        "If you did not expect this invitation, ignore this message.\n"
    )
    adapter = get_notification_adapter(mode=settings.NOTIFICATION_DELIVERY_MODE)
    delivered = adapter.send(
        recipient=invitation.email,
        title="Your PlantProof invitation",
        message=email_body,
        channel="EMAIL",
        metadata={
            "invitation_id": invitation.id,
            "tenant_id": invitation.tenant_id,
            "role": invitation.role,
        },
    )

    if delivered is not False:
        invitation.delivery_status = "SENT"
        invitation.delivered_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(invitation)
    else:
        invitation.delivery_status = "FAILED"
        invitation.delivery_error_code = "EMAIL_DELIVERY_FAILED"
        if settings.ENVIRONMENT in ("production", "staging"):
            invitation.status = "REVOKED"
            invitation.revoked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(invitation)
        if settings.ENVIRONMENT in ("production", "staging"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Invitation delivery failed. The invitation was revoked; verify SMTP and retry.",
            )

    return InvitationCreatedResponse(
        invitation_id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
        delivery_status=invitation.delivery_status,
        expires_at=invitation.expires_at,
        invitation_url=invitation_url if settings.ENVIRONMENT in ("development", "test") else None,
        debug_token=raw_token if settings.ENVIRONMENT in ("development", "test") else None,
    )


@router.post(
    "/invitations/accept",
    response_model=UserSummary,
    dependencies=[Depends(rate_limit(max_requests=8, window_seconds=60, key_prefix="invite_accept"))],
)
def accept_invitation(
    request: AcceptInvitationRequest,
    db: Session = Depends(get_db),
):
    """Redeems a single-use invitation and creates an active account with a user-chosen password."""
    from sqlalchemy import select

    token_hash = hashlib.sha256(request.token.encode("utf-8")).hexdigest()
    invitation = db.scalar(
        select(UserInvitation)
        .where(UserInvitation.token_hash == token_hash)
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    if not invitation or invitation.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This invitation is invalid, expired or already used.")
    if invitation.expires_at <= now:
        invitation.status = "EXPIRED"
        invitation.revoked_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This invitation has expired.")

    existing_user = db.scalar(select(User).where(User.email == invitation.email))
    if existing_user:
        invitation.status = "REVOKED"
        invitation.revoked_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists for this email. Ask an administrator to review the invitation.",
        )

    new_user = User(
        tenant_id=invitation.tenant_id,
        email=invitation.email,
        full_name=invitation.full_name,
        hashed_password=get_password_hash(request.password),
        role=invitation.role,
        is_active=True,
    )
    db.add(new_user)
    db.flush()

    invitation.status = "ACCEPTED"
    invitation.accepted_user_id = new_user.id
    invitation.accepted_at = now
    db.commit()
    db.refresh(new_user)
    return build_user_summary(db, new_user)
