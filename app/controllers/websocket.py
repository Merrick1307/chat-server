from typing import Annotated

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from asyncpg import Connection

from app.dependencies.database import acquire_db_connection
from app.dependencies.cache import get_cache_service, get_ws_manager
from app.utils.jwts import VerifiedTokenData, verify_and_return_jwt_payload
from app.websocket.manager import WebSocketManager
from app.websocket.handler import WebSocketHandler
from app.cache import WebSocketCacheService
from app.services.messaging import MessageService, GroupService, GroupMessageService


router = APIRouter(tags=["websocket"])


@router.websocket("/message")
async def websocket_endpoint(
    websocket: WebSocket,
    db: Annotated[Connection, Depends(acquire_db_connection)],
    auth: Annotated[VerifiedTokenData, Depends(verify_and_return_jwt_payload)],
    manager: Annotated[WebSocketManager, Depends(get_ws_manager)],
    cache: Annotated[WebSocketCacheService, Depends(get_cache_service)],
):
    """
    WebSocket endpoint for real-time messaging.

    Connection URL: ws://host/message (with Authorization header)

    Client -> Server message types:
    - message.send: Send direct message
    - message.group.send: Send group message
    - message.read: Mark message as read
    - typing: Typing indicator
    - ping: Heartbeat

    Server -> Client message types:
    - message.new: New direct message
    - message.group.new: New group message
    - messages.offline: Batch of offline messages
    - message.ack: Message acknowledgment
    - typing: Typing indicator
    - pong: Heartbeat response
    - error: Error message
    """
    user_id = auth.username

    handler = WebSocketHandler(
        manager=manager,
        cache=cache,
        message_service=MessageService(db),
        group_service=GroupService(db),
        group_message_service=GroupMessageService(db),
    )

    async with manager.connection(user_id, websocket):
        await handler.deliver_offline_messages(user_id, websocket)

        try:
            while True:
                raw_message = await websocket.receive_text()
                await handler.handle_message(user_id, websocket, raw_message)
        except WebSocketDisconnect:
            pass


@router.get("/message/status")
async def websocket_status(
    manager: Annotated[WebSocketManager, Depends(get_ws_manager)]
):
    """Get WebSocket server status."""
    return {
        "connected_users": manager.get_connected_user_count(),
        "total_connections": manager.get_total_connection_count()
    }
