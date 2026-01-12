from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import Field

from app.models.base import BaseModelSchema, BaseCreateSchema


class MessageCreate(BaseCreateSchema):
    """Schema for creating a direct message."""
    recipient_id: UUID
    content: str = Field(..., min_length=1, max_length=10000)
    message_type: str = Field(default="text", max_length=20)


class Message(BaseModelSchema):
    """Full message model."""
    message_id: Optional[UUID] = None
    sender_id: UUID
    recipient_id: UUID
    content: str
    message_type: str = "text"
    created_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None


class GroupCreate(BaseCreateSchema):
    """Schema for creating a group."""
    group_name: str = Field(..., min_length=1, max_length=100)
    member_ids: list[UUID] = Field(..., min_length=1)


class Group(BaseModelSchema):
    """Full group model."""
    group_id: Optional[UUID] = None
    group_name: str
    creator_id: UUID
    created_at: Optional[datetime] = None


class GroupMemberCreate(BaseCreateSchema):
    """Schema for adding group members."""
    user_ids: list[UUID] = Field(..., min_length=1)


class GroupMember(BaseModelSchema):
    """Group member model."""
    group_id: UUID
    user_id: UUID
    role: str = "member"
    joined_at: Optional[datetime] = None


class GroupMessageCreate(BaseCreateSchema):
    """Schema for creating a group message."""
    group_id: UUID
    content: str = Field(..., min_length=1, max_length=10000)
    message_type: str = Field(default="text", max_length=20)


class GroupMessage(BaseModelSchema):
    """Full group message model."""
    message_id: Optional[UUID] = None
    group_id: UUID
    sender_id: UUID
    content: str
    message_type: str = "text"
    created_at: Optional[datetime] = None
