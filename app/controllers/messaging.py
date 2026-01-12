from typing import Optional, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from asyncpg import Connection

from app.controllers.base import BaseController
from app.dependencies.database import acquire_db_connection
from app.utils.logs import ErrorLogger
from app.utils.jwts import verify_and_return_jwt_payload, VerifiedTokenData
from app.services.messaging import MessageService, GroupService, GroupMessageService
from app.models.messaging import (
    MessageCreate, GroupCreate, GroupMemberCreate
)
from app.views.responses import APIResponse
from app.views.messaging import (
    ConversationResponse,
    MarkAsReadResponse,
    GroupMembersAddResponse,
    SuccessResponse,
    GroupMessagesResponse,
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
    ) -> ConversationResponse:
        """Get conversation history between two users."""
        messages = await self._message_service.get_conversation(
            user_id, other_user_id, limit, offset
        )
        total = await self._message_service.get_conversation_count(user_id, other_user_id)
        
        return ConversationResponse(
            messages=messages,
            total=total,
            has_more=offset + limit < total
        )
    
    async def get_unread_messages(self, user_id: str) -> list:
        """Get unread messages for a user."""
        return await self._message_service.get_unread_messages(user_id)
    
    async def mark_as_read(self, message_id: str, user_id: str) -> MarkAsReadResponse:
        """Mark a message as read."""
        success = await self._message_service.mark_as_read(message_id, user_id)
        return MarkAsReadResponse(success=success)
    
    async def get_conversations_list(self, user_id: str) -> list:
        """Get list of all conversation partners with last message and unread count."""
        return await self._message_service.get_conversations_list(user_id)


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
        return GroupMembersAddResponse(success=True, added_count=added)
    
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
        return SuccessResponse(success=success)
    
    async def get_group_messages(
        self,
        group_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> GroupMessagesResponse:
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
        
        return GroupMessagesResponse(
            messages=messages,
            total=total,
            has_more=offset + limit < total
        )
    
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


router = APIRouter(prefix="/api/v1/messages", tags=["Messages"])
group_router = APIRouter(prefix="/api/v1/groups", tags=["Groups"])


@router.post(
    "/send",
    summary="Send direct message",
    description="Send a direct message to another user via REST API. For real-time messaging, use WebSocket instead."
)
async def send_message(
    request: MessageCreate,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """
    Send a direct message to another user.
    
    - **recipient_id**: UUID of the recipient user
    - **content**: Message text content
    - **message_type**: Type of message (default: "text")
    
    Returns the saved message with server-generated ID and timestamp.
    """
    controller = MessageController(db)
    result = await controller.send_message(
        sender_id=auth.user_id,
        recipient_id=str(request.recipient_id),
        content=request.content,
        message_type=request.message_type
    )
    return APIResponse(data=result, message="Message sent")


@router.get(
    "/conversations",
    summary="Get conversation list",
    description="Get list of all users the current user has exchanged messages with, including last message preview and unread count."
)
async def get_conversations_list(
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """
    Get all conversation partners for the current user.
    
    Returns a list of conversation summaries ordered by most recent message, each containing:
    - **partner_id**: UUID of the conversation partner
    - **username**: Partner's username
    - **display_name**: Partner's display name (full name or username)
    - **last_message**: Preview of the most recent message
    - **last_message_at**: Timestamp of the most recent message
    - **unread_count**: Number of unread messages from this partner
    """
    controller = MessageController(db)
    result = await controller.get_conversations_list(auth.user_id)
    return APIResponse(data=result)


@router.get(
    "/conversation/{user_id}",
    summary="Get conversation history",
    description="Get paginated message history with a specific user."
)
async def get_conversation(
    user_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
    limit: int = Query(default=50, ge=1, le=100, description="Number of messages to retrieve"),
    offset: int = Query(default=0, ge=0, description="Number of messages to skip"),
):
    """
    Get message history between the current user and another user.
    
    - **user_id**: UUID of the other user in the conversation
    - **limit**: Maximum number of messages to return (1-100, default 50)
    - **offset**: Number of messages to skip for pagination
    
    Returns messages ordered chronologically (oldest first) with pagination metadata.
    """
    controller = MessageController(db)
    result = await controller.get_conversation(
        user_id=auth.user_id,
        other_user_id=str(user_id),
        limit=limit,
        offset=offset
    )
    return APIResponse(data=result)


@router.get(
    "/unread",
    summary="Get unread messages",
    description="Get all unread messages for the current user across all conversations."
)
async def get_unread_messages(
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """
    Get all unread messages for the current user.
    
    Returns messages where the current user is the recipient and read_at is null.
    Messages are ordered by creation time (newest first) and include sender information.
    """
    controller = MessageController(db)
    result = await controller.get_unread_messages(auth.user_id)
    return APIResponse(data=result)


@router.post(
    "/{message_id}/read",
    summary="Mark message as read",
    description="Mark a specific message as read by the current user."
)
async def mark_message_read(
    message_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """
    Mark a message as read.
    
    - **message_id**: UUID of the message to mark as read
    
    Only works if the current user is the recipient of the message.
    Sets the read_at timestamp to the current time.
    """
    controller = MessageController(db)
    result = await controller.mark_as_read(str(message_id), auth.user_id)
    return APIResponse(data=result, message="Message marked as read")


@group_router.post(
    "",
    summary="Create group",
    description="Create a new group chat with specified members."
)
async def create_group(
    request: GroupCreate,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """
    Create a new group chat.
    
    - **group_name**: Name of the group
    - **member_ids**: List of user UUIDs to add as initial members
    
    The creating user is automatically added as a member with admin role.
    Returns the created group details including group_id.
    """
    controller = GroupController(db)
    result = await controller.create_group(
        creator_id=auth.user_id,
        group_name=request.group_name,
        member_ids=[str(uid) for uid in request.member_ids]
    )
    return APIResponse(data=result, message="Group created")


@group_router.get(
    "/my",
    summary="Get my groups",
    description="Get all groups the current user is a member of."
)
async def get_my_groups(
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """
    Get all groups the current user belongs to.
    
    Returns a list of group summaries including group_id, group_name,
    member count, and creation date.
    """
    controller = GroupController(db)
    result = await controller.get_user_groups(auth.user_id)
    return APIResponse(data=result)


@group_router.get(
    "/{group_id}",
    summary="Get group details",
    description="Get detailed information about a specific group."
)
async def get_group(
    group_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """
    Get details of a specific group.
    
    - **group_id**: UUID of the group
    
    Requires the current user to be a member of the group.
    Returns group metadata and settings.
    """
    controller = GroupController(db)
    result = await controller.get_group(str(group_id), auth.user_id)
    return APIResponse(data=result)


@group_router.get(
    "/{group_id}/members",
    summary="Get group members",
    description="Get list of all members in a group."
)
async def get_group_members(
    group_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """
    Get all members of a group.
    
    - **group_id**: UUID of the group
    
    Requires the current user to be a member of the group.
    Returns list of members with their user info and role in the group.
    """
    controller = GroupController(db)
    result = await controller.get_group_members(str(group_id), auth.user_id)
    return APIResponse(data=result)


@group_router.post(
    "/{group_id}/members",
    summary="Add group members",
    description="Add new members to an existing group."
)
async def add_group_members(
    group_id: UUID,
    request: GroupMemberCreate,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """
    Add members to a group.
    
    - **group_id**: UUID of the group
    - **user_ids**: List of user UUIDs to add
    
    Requires the current user to be a member of the group.
    Returns success status and number of members added.
    """
    controller = GroupController(db)
    result = await controller.add_members(
        group_id=str(group_id),
        user_id=auth.user_id,
        member_ids=[str(uid) for uid in request.user_ids]
    )
    return APIResponse(data=result, message="Members added")


@group_router.delete(
    "/{group_id}/members/{user_id}",
    summary="Remove group member",
    description="Remove a member from a group."
)
async def remove_group_member(
    group_id: UUID,
    user_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
):
    """
    Remove a member from a group.
    
    - **group_id**: UUID of the group
    - **user_id**: UUID of the user to remove
    
    Requires the current user to be a member of the group.
    Users can remove themselves to leave the group.
    """
    controller = GroupController(db)
    result = await controller.remove_member(
        group_id=str(group_id),
        user_id=auth.user_id,
        target_user_id=str(user_id)
    )
    return APIResponse(data=result, message="Member removed")


@group_router.get(
    "/{group_id}/messages",
    summary="Get group messages",
    description="Get paginated message history for a group."
)
async def get_group_messages(
    group_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
    limit: int = Query(default=50, ge=1, le=100, description="Number of messages to retrieve"),
    offset: int = Query(default=0, ge=0, description="Number of messages to skip"),
):
    """
    Get message history for a group.
    
    - **group_id**: UUID of the group
    - **limit**: Maximum number of messages to return (1-100, default 50)
    - **offset**: Number of messages to skip for pagination
    
    Requires the current user to be a member of the group.
    Returns messages ordered chronologically with sender information.
    """
    controller = GroupController(db)
    result = await controller.get_group_messages(
        group_id=str(group_id),
        user_id=auth.user_id,
        limit=limit,
        offset=offset
    )
    return APIResponse(data=result)
