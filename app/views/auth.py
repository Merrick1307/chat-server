from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.views.base import BaseView


class SignupRequest(BaseModel):
    """Request schema for user signup."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """Request schema for user login."""
    username: str = Field(..., description="Username or email")
    password: str


class LogoutRequest(BaseModel):
    """Request schema for user logout."""
    refresh_token: str


class RefreshRequest(BaseModel):
    """Request schema for token refresh."""
    refresh_token: str


@dataclass(slots=True)
class TokenResponse(BaseView):
    """Response schema containing auth tokens."""
    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900


@dataclass(slots=True)
class LogoutResponse(BaseView):
    """Response schema for logout."""
    success: bool


@dataclass(slots=True)
class SessionResponse(BaseView):
    """Response schema for session check."""
    valid: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Request schema for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Request schema for password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8)