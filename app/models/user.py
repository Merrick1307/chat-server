from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from app.models.base import BaseModelSchema, BaseCreateSchema


class UserCreate(BaseCreateSchema):
    """Schema for user creation request."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)


class User(BaseModelSchema):
    """Full user model."""
    id: Optional[UUID] = None
    username: str
    email: str
    password: str
    first_name: str
    last_name: str
