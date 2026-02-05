from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class UpdateRoleRequest(BaseModel):
    """Request to update a user's role."""
    role: str


class CreateGroupRequest(BaseModel):
    """Request to create a new group as admin."""
    group_name: str
    member_ids: list[UUID]


class AdminUserSearchParams(BaseModel):
    """Query parameters for admin user search."""
    limit: int = 50
    offset: int = 0
    search: Optional[str] = None
