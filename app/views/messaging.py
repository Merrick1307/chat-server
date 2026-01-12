from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel

from app.views.base import BaseView


@dataclass(slots=True)
class MessageData(BaseView):
    """Response data for a single message."""
    message_id: str
    sender_id: str
    recipient_id: str
    content: str
    message_type: str
    created_at: Any
    delivered_at: Optional[Any] = None
    read_at: Optional[Any] = None
    sender_username: Optional[str] = None


@dataclass(slots=True)
class ConversationResponse(BaseView):
    """Response for conversation history."""
    messages: List[dict] = field(default_factory=list)
    total: int = 0
    has_more: bool = False


@dataclass(slots=True)
class ConversationSummary(BaseView):
    """Summary of a conversation for the conversations list."""
    partner_id: str
    username: str
    display_name: str
    last_message: Optional[str] = None
    last_message_at: Optional[Any] = None
    unread_count: int = 0


@dataclass(slots=True)
class MarkAsReadResponse(BaseView):
    """Response for mark as read operation."""
    success: bool = True


@dataclass(slots=True)
class GroupData(BaseView):
    """Response data for a single group."""
    group_id: str
    group_name: str
    creator_id: str
    created_at: Any
    member_count: Optional[int] = None


@dataclass(slots=True)
class GroupMemberData(BaseView):
    """Response data for a group member."""
    user_id: str
    username: str
    display_name: Optional[str] = None
    role: str = "member"
    joined_at: Optional[Any] = None


@dataclass(slots=True)
class GroupMembersAddResponse(BaseView):
    """Response for adding members to a group."""
    success: bool = True
    added_count: int = 0


@dataclass(slots=True)
class SuccessResponse(BaseView):
    """Generic success response."""
    success: bool = True


@dataclass(slots=True)
class GroupMessagesResponse(BaseView):
    """Response for group message history."""
    messages: List[dict] = field(default_factory=list)
    total: int = 0
    has_more: bool = False


class ClientMessage(BaseModel):
    """Client message schema for direct messages."""
    recipient_id: str
    content: str
    message_type: str = "text"
    type: str = "message.send"


class ClientGroupMessage(BaseModel):
    """Client message schema for group messages."""
    group_id: str
    content: str
    message_type: str = "text"
    type: str = "message.group.send"


class ClientReadReceipt(BaseModel):
    """Client read receipt."""
    message_id: str
    type: str = "message.read"


class ClientTyping(BaseModel):
    """Client typing indicator."""
    recipient_id: Optional[str] = None
    group_id: Optional[str] = None
    type: str = "typing"


# Server -> Client (no validation needed, hence python native dataclass)

@dataclass(slots=True)
class ServerMessage(BaseView):
    """Server response for direct message."""
    type: str
    message_id: str
    sender_id: str
    recipient_id: str
    content: str
    message_type: str
    created_at: str
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ServerGroupMessage(BaseView):
    """Server response for group message."""
    type: str
    message_id: str
    group_id: str
    sender_id: str
    content: str
    message_type: str
    created_at: str
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ServerMessageAck(BaseView):
    """Server acknowledgment for sent message."""
    type: str
    message_id: str
    status: str
    timestamp: str
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ServerReadReceipt(BaseView):
    """Server read receipt notification."""
    type: str
    message_id: str
    reader_id: str
    read_at: str
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ServerTyping(BaseView):
    """Server typing indicator."""
    type: str
    user_id: str
    recipient_id: Optional[str] = None
    group_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ServerOfflineMessages(BaseView):
    """Server batch of offline messages."""
    type: str
    messages: List[dict] = field(default_factory=list)
    count: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ServerError(BaseView):
    """Server error response."""
    type: str
    error: str
    code: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ServerPong(BaseView):
    """Server pong response."""
    type: str = "pong"
    timestamp: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
