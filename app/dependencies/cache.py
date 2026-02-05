from typing import Union

from fastapi.requests import Request
from fastapi.websockets import WebSocket

from app.cache import WebSocketCacheService


async def get_redis_client(request: Request):
    return request.app.state.redis


async def get_cache_service(websocket: WebSocket) -> WebSocketCacheService:
    """Get WebSocket cache service from app state."""
    return websocket.app.state.ws_cache


async def get_ws_manager(websocket: WebSocket):
    """Get WebSocket manager from app state."""
    return websocket.app.state.ws_manager


async def get_ws_manager_http(request: Request):
    """Get WebSocket manager from app state for HTTP endpoints."""
    return request.app.state.ws_manager
