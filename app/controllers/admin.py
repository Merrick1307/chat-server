from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from asyncpg import Connection
from redis.asyncio import Redis

from app.controllers.base import BaseController
from app.dependencies.database import acquire_db_connection
from app.dependencies.cache import get_ws_manager_http, get_redis_client
from app.services.admin import AdminService
from app.cache import TokenCacheService
from app.utils.guards import require_admin
from app.utils.jwts import VerifiedTokenData
from app.views import APIResponse, UpdateRoleRequest, CreateGroupRequest
from app.websocket.manager import WebSocketManager


router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


class AdminController(BaseController):
    """Controller for admin operations."""
    
    def __init__(self, db: Connection, ws_manager: Optional[WebSocketManager] = None):
        super().__init__(db)
        self._admin_service = AdminService(db)
        self._ws_manager = ws_manager
    
    @property
    def admin_service(self) -> AdminService:
        return self._admin_service


@router.get(
    "/users",
    summary="List all users",
    description="Get paginated list of all users. Admin only."
)
async def list_users(
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(require_admin)],
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None, description="Search by username, email, or name")
):
    """
    List all users with optional search.
    
    - **limit**: Maximum users to return (1-100)
    - **offset**: Number of users to skip
    - **search**: Optional search term for username, email, or name
    """
    controller = AdminController(db)
    result = await controller.admin_service.get_all_users(limit, offset, search)
    return APIResponse(data=result)


@router.get(
    "/users/online",
    summary="Get online users",
    description="Get list of currently online users. Admin only."
)
async def get_online_users(
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(require_admin)],
    ws_manager: Annotated[WebSocketManager, Depends(get_ws_manager_http)],
):
    """
    Get all currently connected users via WebSocket.
    """
    online_user_ids = ws_manager.get_connected_users()
    
    if not online_user_ids:
        return APIResponse(data={"online_users": [], "count": 0})
    
    users = await db.fetch(
        """
        SELECT id::text as user_id, username, first_name, last_name
        FROM users
        WHERE id = ANY($1::uuid[])
        """,
        online_user_ids
    )
    
    return APIResponse(data={
        "online_users": [dict(u) for u in users],
        "count": len(users)
    })


@router.get(
    "/users/{user_id}",
    summary="Get user details",
    description="Get detailed information about a specific user. Admin only."
)
async def get_user_detail(
    user_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(require_admin)],
):
    """
    Get detailed user information including message and group counts.
    """
    controller = AdminController(db)
    result = await controller.admin_service.get_user_detail(str(user_id))
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return APIResponse(data=result)


@router.delete(
    "/users/{user_id}",
    summary="Delete user",
    description="Delete a user and all their associated data. Admin only."
)
async def delete_user(
    user_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(require_admin)],
):
    """
    Delete a user from the system.
    
    - Cannot delete your own account
    - Cannot delete other admins
    """
    controller = AdminController(db)
    
    try:
        await controller.admin_service.delete_user(str(user_id), auth.user_id)
        return APIResponse(data={"success": True}, message="User deleted")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch(
    "/users/{user_id}/role",
    summary="Update user role",
    description="Change a user's role. Admin only."
)
async def update_user_role(
    user_id: UUID,
    request: UpdateRoleRequest,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(require_admin)],
):
    """
    Update a user's role.
    
    - **role**: New role ('user' or 'admin')
    - Cannot change your own role
    """
    controller = AdminController(db)
    
    try:
        await controller.admin_service.update_user_role(
            str(user_id), request.role, auth.user_id
        )
        return APIResponse(data={"success": True}, message=f"Role updated to {request.role}")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/groups",
    summary="List all groups",
    description="Get paginated list of all groups. Admin only."
)
async def list_groups(
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(require_admin)],
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    List all groups with member counts.
    """
    controller = AdminController(db)
    result = await controller.admin_service.get_all_groups(limit, offset)
    return APIResponse(data=result)


@router.get(
    "/groups/{group_id}",
    summary="Get group details",
    description="Get detailed information about a specific group. Admin only."
)
async def get_group_detail(
    group_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(require_admin)],
):
    """
    Get detailed group information including all members.
    """
    controller = AdminController(db)
    result = await controller.admin_service.get_group_detail(str(group_id))
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    return APIResponse(data=result)


@router.post(
    "/groups",
    summary="Create group",
    description="Create a new group as admin. Admin only."
)
async def create_group(
    request: CreateGroupRequest,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(require_admin)],
):
    """
    Create a new group with specified members.
    The admin becomes the group creator.
    """
    controller = AdminController(db)
    result = await controller.admin_service.create_group(
        request.group_name,
        auth.user_id,
        [str(uid) for uid in request.member_ids]
    )
    return APIResponse(data=result, message="Group created")


@router.delete(
    "/groups/{group_id}",
    summary="Delete group",
    description="Delete a group and all its messages. Admin only."
)
async def delete_group(
    group_id: UUID,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(require_admin)],
):
    """
    Delete a group and all associated messages.
    """
    controller = AdminController(db)
    
    try:
        await controller.admin_service.delete_group(str(group_id), auth.user_id)
        return APIResponse(data={"success": True}, message="Group deleted")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/stats",
    summary="Get system statistics",
    description="Get overall system statistics. Admin only."
)
async def get_stats(
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(require_admin)],
    ws_manager: Annotated[WebSocketManager, Depends(get_ws_manager_http)],
):
    """
    Get system-wide statistics.
    """
    user_count = await db.fetchval("SELECT COUNT(*) FROM users")
    group_count = await db.fetchval("SELECT COUNT(*) FROM groups")
    message_count = await db.fetchval("SELECT COUNT(*) FROM messages")
    group_message_count = await db.fetchval("SELECT COUNT(*) FROM group_messages")
    
    return APIResponse(data={
        "total_users": user_count,
        "total_groups": group_count,
        "total_direct_messages": message_count,
        "total_group_messages": group_message_count,
        "online_users": ws_manager.get_connected_user_count(),
        "active_connections": ws_manager.get_total_connection_count()
    })


@router.get(
    "/tokens/reset",
    summary="Get active password reset tokens",
    description="View all active password reset tokens for introspection. Admin only."
)
async def get_reset_tokens(
    auth: Annotated[VerifiedTokenData, Depends(require_admin)],
    redis: Annotated[Redis, Depends(get_redis_client)],
):
    """
    Get all active password reset tokens.
    Useful for debugging and monitoring reset requests.
    """
    token_service = TokenCacheService(redis)
    tokens = await token_service.get_all_reset_tokens()
    return APIResponse(data={"tokens": tokens, "count": len(tokens)})


@router.delete(
    "/tokens/reset/{token_hash}",
    summary="Invalidate a password reset token",
    description="Manually invalidate a password reset token. Admin only."
)
async def invalidate_reset_token(
    token_hash: str,
    auth: Annotated[VerifiedTokenData, Depends(require_admin)],
    redis: Annotated[Redis, Depends(get_redis_client)],
):
    """
    Manually invalidate a specific reset token by its hash.
    """
    from app.cache.keys import RedisKeys
    key = RedisKeys.password_reset_token(token_hash)
    deleted = await redis.delete(key)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found or already expired"
        )
    
    return APIResponse(data={"success": True}, message="Token invalidated")
