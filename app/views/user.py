from dataclasses import dataclass
from uuid import UUID

from app.views.base import BaseView


@dataclass(slots=True)
class UserProfile(BaseView):
    """User profile view response."""
    id: UUID
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    created_at: str
    updated_at: str
