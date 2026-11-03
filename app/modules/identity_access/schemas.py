"""
Identity & Access Pydantic Schemas
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserSummary(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    tenant_id: str
    tenant_name: Optional[str] = None
    plant_ids: List[str] = []

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserSummary


class UserInviteRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "PLANT_MANAGER"
    plant_ids: List[str] = []


class InvitationCreatedResponse(BaseModel):
    invitation_id: str
    email: EmailStr
    role: str
    status: str
    delivery_status: str
    expires_at: datetime
    invitation_url: Optional[str] = None
    # Only returned in development/test. Never returned in production.
    debug_token: Optional[str] = None


class AcceptInvitationRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    password: str = Field(min_length=12, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetRequestResponse(BaseModel):
    message: str
    # Only returned in development/test to support local testing.
    debug_token: Optional[str] = None


class PasswordResetCompleteRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    new_password: str = Field(min_length=12, max_length=128)


class UserListItem(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    tenant_id: str
    tenant_name: Optional[str] = None
    plant_ids: List[str] = []
    is_active: bool = True
    created_at: str

    model_config = {"from_attributes": True}

