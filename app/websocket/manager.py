from contextlib import asynccontextmanager
from typing import Set, Dict, Optional, Any
import asyncio
import orjson

from fastapi.websockets import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from app.cache import WebSocketCacheService


class WebSocketManager:
    """Manages WebSocket connections and message routing."""
    
    MAX_CONNECTIONS_PER_USER = 5
    
    def __init__(self, redis_client: Redis, cache: WebSocketCacheService):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._ws_to_user: Dict[WebSocket, str] = {}
        self.redis = redis_client
        self.cache = cache
    
    @asynccontextmanager
    async def connection(self, user_id: str, websocket: WebSocket):
        """Context manager for WebSocket connection lifecycle."""
        connected: bool = False
        try:
            await websocket.accept()
            
            if user_id in self.active_connections:
                if len(self.active_connections[user_id]) >= self.MAX_CONNECTIONS_PER_USER:
                    await websocket.close(code=4000, reason="Too many connections")
                    raise ConnectionRefusedError("Too many connections")
            
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            
            self.active_connections[user_id].add(websocket)
            self._ws_to_user[websocket] = user_id
            connected = True
            
            await self._set_user_online(user_id)
            
            yield websocket
            
        finally:
            if connected:
                await self._disconnect(user_id, websocket)
    
    async def _disconnect(self, user_id: str, websocket: WebSocket) -> None:
        """Handle WebSocket disconnection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                await self._set_user_offline(user_id)
        
        self._ws_to_user.pop(websocket, None)
    
    async def _set_user_online(self, user_id: str) -> None:
        """Mark user as online in Redis."""
        await self.cache.set_user_online(user_id)
    
    async def _set_user_offline(self, user_id: str) -> None:
        """Mark user as offline in Redis."""
        await self.cache.set_user_offline(user_id)
    
    def is_user_online_local(self, user_id: str) -> bool:
        """Check if user has active connections on this server."""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
    
    async def is_user_online(self, user_id: str) -> bool:
        """Check if user is online (via Redis for distributed check)."""
        return await self.cache.is_user_online(user_id)
    
    async def send_to_user(self, user_id: str, message: dict) -> bool:
        """Send message to all connections of a user. Returns True if sent."""
        if user_id not in self.active_connections:
            return False
        
        connections = self.active_connections[user_id].copy()
        if not connections:
            return False
        
        message_json = orjson.dumps(message).decode()
        disconnected = []
        
        for ws in connections:
            try:
                await ws.send_text(message_json)
            except Exception:
                disconnected.append(ws)
        
        for ws in disconnected:
            await self._disconnect(user_id, ws)
        
        return len(disconnected) < len(connections)
    
    async def send_to_users(self, user_ids: list[str], message: dict, exclude_user: Optional[str] = None) -> list[str]:
        """Send message to multiple users. Returns list of users who received it."""
        delivered_to = []
        for user_id in user_ids:
            if exclude_user and user_id == exclude_user:
                continue
            if await self.send_to_user(user_id, message):
                delivered_to.append(user_id)
        return delivered_to
    
    async def broadcast_to_group(
        self, 
        member_ids: list[str], 
        message: dict, 
        exclude_user: Optional[str] = None
    ) -> tuple[list[str], list[str]]:
        """
        Broadcast message to group members.
        Returns (delivered_to, offline_users) tuple.
        """
        delivered_to = []
        offline_users = []
        
        for user_id in member_ids:
            if exclude_user and user_id == exclude_user:
                continue
            
            if self.is_user_online_local(user_id):
                if await self.send_to_user(user_id, message):
                    delivered_to.append(user_id)
                else:
                    offline_users.append(user_id)
            else:
                offline_users.append(user_id)
        
        return delivered_to, offline_users
    
    async def refresh_heartbeat(self, user_id: str) -> None:
        """Refresh user's online status TTL."""
        await self.cache.refresh_heartbeat(user_id)
    
    def get_user_from_websocket(self, websocket: WebSocket) -> Optional[str]:
        """Get user_id from websocket connection."""
        return self._ws_to_user.get(websocket)
    
    def get_connected_user_count(self) -> int:
        """Get total number of connected users on this server."""
        return len(self.active_connections)
    
    def get_total_connection_count(self) -> int:
        """Get total number of WebSocket connections on this server."""
        return sum(len(conns) for conns in self.active_connections.values())
    
    def get_connected_users(self) -> list[str]:
        """Get list of all connected user IDs."""
        return list(self.active_connections.keys())
