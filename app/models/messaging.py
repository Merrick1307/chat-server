from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import Field

from app.models.base import BaseModelSchema, BaseCreateSchema, BaseResponseSchema


# Direct Message Models

class MessageCreate(BaseCreateSchema):
    """Schema for creating a direct message."""
    recipient_id: UUID
    content: str = Field(..., min_length=1, max_length=10000)
    message_type: str = Field(default="text", max_length=20)


class MessageResponse(BaseResponseSchema):
    """Schema for message response."""
    message_id: UUID
    sender_id: UUID
    recipient_id: UUID
    content: str
    message_type: str
    created_at: datetime
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None


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


# Group Models

class GroupCreate(BaseCreateSchema):
    """Schema for creating a group."""
    group_name: str = Field(..., min_length=1, max_length=100)
    member_ids: list[UUID] = Field(..., min_length=1)


class GroupResponse(BaseResponseSchema):
    """Schema for group response."""
    group_id: UUID
    group_name: str
    creator_id: UUID
    created_at: datetime
    member_count: Optional[int] = None


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


class GroupMemberResponse(BaseResponseSchema):
    """Schema for group member response."""
    user_id: UUID
    username: str
    role: str
    joined_at: datetime


# Group Message Models

class GroupMessageCreate(BaseCreateSchema):
    """Schema for creating a group message."""
    group_id: UUID
    content: str = Field(..., min_length=1, max_length=10000)
    message_type: str = Field(default="text", max_length=20)


class GroupMessageResponse(BaseResponseSchema):
    """Schema for group message response."""
    message_id: UUID
    group_id: UUID
    sender_id: UUID
    content: str
    message_type: str
    created_at: datetime


class GroupMessage(BaseModelSchema):
    """Full group message model."""
    message_id: Optional[UUID] = None
    group_id: UUID
    sender_id: UUID
    content: str
    message_type: str = "text"
    created_at: Optional[datetime] = None


# Conversation Models

class ConversationRequest(BaseModelSchema):
    """Request schema for fetching conversation."""
    user_id: UUID
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ConversationResponse(BaseResponseSchema):
    """Response schema for conversation history."""
    messages: list[MessageResponse]
    total: int
    has_more: bool
