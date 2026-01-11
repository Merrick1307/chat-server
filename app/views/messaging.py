from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel

from app.views.base import BaseView


# Client -> Server (needs validation, hence Pydantic)

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
