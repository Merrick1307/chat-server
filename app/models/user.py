import uuid
from dataclasses import dataclass

from pydantic import BaseModel


class User(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    password: str
    first_name: str
    last_name: str


@dataclass(slots=True)
class UserProfile:
    id: uuid.UUID
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    created_at: str
    updated_at: str