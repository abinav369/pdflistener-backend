from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── User ──────────────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    notifications_enabled: bool
    dark_mode: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    dark_mode: Optional[bool] = None
