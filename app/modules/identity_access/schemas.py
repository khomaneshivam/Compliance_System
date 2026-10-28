"""
Identity & Access Pydantic Schemas
"""

from typing import Optional, List
from pydantic import BaseModel, EmailStr


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

