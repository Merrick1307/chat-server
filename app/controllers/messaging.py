from typing import Optional, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from asyncpg import Connection

from app.controllers.base import BaseController
from app.dependencies.database import acquire_db_connection
from app.utils.logs import ErrorLogger, get_error_logger
from app.utils.jwts import verify_and_return_jwt_payload, VerifiedTokenData
from app.services.messaging import MessageService, GroupService, GroupMessageService
from app.models.messaging import (
    MessageCreate, MessageResponse,
    GroupCreate, GroupResponse,
    GroupMemberCreate, GroupMemberResponse,
    GroupMessageCreate, GroupMessageResponse,
    ConversationResponse,
)


class MessageController(BaseController):
    """Controller for direct message operations."""
    
    def __init__(self, db: Connection, logger: Optional[ErrorLogger] = None):
        super().__init__(db, logger)
        self._message_service = MessageService(db, logger)
    
    async def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        content: str,
        message_type: str = "text"
    ) -> dict:
        """Send a direct message (REST API alternative to WebSocket)."""
        from uuid import uuid4
        message_id = str(uuid4())
        
        result = await self._message_service.save_direct_message(
            message_id=message_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            content=content,
            message_type=message_type
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save message"
            )
        
        return result
    
    async def get_conversation(
        self,
        user_id: str,
        other_user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        """Get conversation history between two users."""
        messages = await self._message_service.get_conversation(
            user_id, other_user_id, limit, offset
        )
        total = await self._message_service.get_conversation_count(user_id, other_user_id)
        
        return {
            "messages": messages,
            "total": total,
            "has_more": offset + limit < total
        }
    
    async def get_unread_messages(self, user_id: str) -> list:
        """Get unread messages for a user."""
        return await self._message_service.get_unread_messages(user_id)
    
    async def mark_as_read(self, message_id: str, user_id: str) -> dict:
        """Mark a message as read."""
        success = await self._message_service.mark_as_read(message_id, user_id)
        return {"success": success}


class GroupController(BaseController):
    """Controller for group operations."""
    
    def __init__(self, db: Connection, logger: Optional[ErrorLogger] = None):
        super().__init__(db, logger)
        self._group_service = GroupService(db, logger)
        self._group_message_service = GroupMessageService(db, logger)
    
    async def create_group(
        self,
        creator_id: str,
        group_name: str,
        member_ids: list[str]
    ) -> dict:
        """Create a new group."""
        result = await self._group_service.create_group(
            creator_id=creator_id,
            group_name=group_name,
            member_ids=member_ids
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create group"
            )
        
        return result
    
    async def get_group(self, group_id: str, user_id: str) -> dict:
        """Get group details."""
        if not await self._group_service.is_member(group_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this group"
            )
        
        group = await self._group_service.get_group(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )
        
        return group
    
    async def add_members(
        self,
        group_id: str,
        user_id: str,
        member_ids: list[str]
    ) -> dict:
        """Add members to a group."""
        role = await self._group_service.get_member_role(group_id, user_id)
        if role not in ("admin", "creator"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can add members"
            )
        
        added = await self._group_service.add_members(group_id, member_ids)
        return {"success": True, "added_count": added}
    
    async def remove_member(
        self,
        group_id: str,
        user_id: str,
        target_user_id: str
    ) -> dict:
        """Remove a member from a group."""
        if user_id != target_user_id:
            role = await self._group_service.get_member_role(group_id, user_id)
            if role not in ("admin", "creator"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can remove other members"
                )
        
        success = await self._group_service.remove_member(group_id, target_user_id)
        return {"success": success}
    
    async def get_group_messages(
        self,
        group_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        """Get messages for a group."""
        if not await self._group_service.is_member(group_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this group"
            )
        
        messages = await self._group_message_service.get_group_messages(
            group_id, limit, offset
        )
        total = await self._group_message_service.get_group_message_count(group_id)
        
        return {
            "messages": messages,
            "total": total,
            "has_more": offset + limit < total
        }
    
    async def get_user_groups(self, user_id: str) -> list:
        """Get all groups a user belongs to."""
        return await self._group_service.get_user_groups(user_id)
    
    async def get_group_members(self, group_id: str, user_id: str) -> list:
        """Get detailed member list for a group."""
        if not await self._group_service.is_member(group_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this group"
            )
        
        return await self._group_service.get_group_members_detail(group_id)


# Router and endpoints

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])
group_router = APIRouter(prefix="/api/v1/groups", tags=["groups"])


# Message endpoints

@router.post("/send")
async def send_message(
    request: MessageCreate,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """Send a direct message via REST API."""
    controller = MessageController(db)
    return await controller.send_message(
        sender_id=auth.username,
        recipient_id=str(request.recipient_id),
        content=request.content,
        message_type=request.message_type
    )


@router.get("/conversation/{user_id}")
async def get_conversation(
    user_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Get conversation history with a user."""
    controller = MessageController(db)
    return await controller.get_conversation(
        user_id=auth.username,
        other_user_id=str(user_id),
        limit=limit,
        offset=offset
    )


@router.get("/unread")
async def get_unread_messages(
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """Get unread messages."""
    controller = MessageController(db)
    return await controller.get_unread_messages(auth.username)


@router.post("/{message_id}/read")
async def mark_message_read(
    message_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """Mark a message as read."""
    controller = MessageController(db)
    return await controller.mark_as_read(str(message_id), auth.username)


# Group endpoints

@group_router.post("")
async def create_group(
    request: GroupCreate,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """Create a new group."""
    controller = GroupController(db)
    return await controller.create_group(
        creator_id=auth.username,
        group_name=request.group_name,
        member_ids=[str(uid) for uid in request.member_ids]
    )


@group_router.get("/my")
async def get_my_groups(
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """Get groups the current user belongs to."""
    controller = GroupController(db)
    return await controller.get_user_groups(auth.username)


@group_router.get("/{group_id}")
async def get_group(
    group_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """Get group details."""
    controller = GroupController(db)
    return await controller.get_group(str(group_id), auth.username)


@group_router.get("/{group_id}/members")
async def get_group_members(
    group_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """Get group members."""
    controller = GroupController(db)
    return await controller.get_group_members(str(group_id), auth.username)


@group_router.post("/{group_id}/members")
async def add_group_members(
    group_id: UUID,
    request: GroupMemberCreate,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """Add members to a group."""
    controller = GroupController(db)
    return await controller.add_members(
        group_id=str(group_id),
        user_id=auth.username,
        member_ids=[str(uid) for uid in request.user_ids]
    )


@group_router.delete("/{group_id}/members/{user_id}")
async def remove_group_member(
    group_id: UUID,
    user_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """Remove a member from a group."""
    controller = GroupController(db)
    return await controller.remove_member(
        group_id=str(group_id),
        user_id=auth.username,
        target_user_id=str(user_id)
    )


@group_router.get("/{group_id}/messages")
async def get_group_messages(
    group_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Get messages for a group."""
    controller = GroupController(db)
    return await controller.get_group_messages(
        group_id=str(group_id),
        user_id=auth.username,
        limit=limit,
        offset=offset
    )
