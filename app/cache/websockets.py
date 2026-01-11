from typing import Optional
import json

from redis.asyncio import Redis

from app.cache.keys import RedisKeys


class WebSocketCacheService:
    """Service for managing WebSocket-related Redis operations."""
    
    def __init__(self, redis_client: Redis):
        self._redis = redis_client
    
    @property
    def redis(self) -> Redis:
        return self._redis
    
    async def set_user_online(self, user_id: str) -> None:
        """Mark user as online."""
        key = RedisKeys.user_online(user_id)
        await self._redis.set(key, "1", ex=RedisKeys.ONLINE_TTL)
    
    async def set_user_offline(self, user_id: str) -> None:
        """Mark user as offline."""
        key = RedisKeys.user_online(user_id)
        await self._redis.delete(key)
    
    async def is_user_online(self, user_id: str) -> bool:
        """Check if user is online."""
        key = RedisKeys.user_online(user_id)
        result = await self._redis.get(key)
        return result is not None
    
    async def refresh_heartbeat(self, user_id: str) -> None:
        """Refresh user's online status TTL."""
        key = RedisKeys.user_online(user_id)
        await self._redis.expire(key, RedisKeys.ONLINE_TTL)
    
    async def queue_offline_message(
        self,
        user_id: str,
        message_id: str,
        message_type: str = "direct",
        group_id: Optional[str] = None
    ) -> None:
        """Queue a message for offline user."""
        key = RedisKeys.offline_queue(user_id)
        payload = {
            "message_id": message_id,
            "type": message_type
        }
        if group_id:
            payload["group_id"] = group_id
        
        await self._redis.lpush(key, json.dumps(payload))
        await self._redis.expire(key, RedisKeys.OFFLINE_QUEUE_TTL)
    
    async def get_offline_queue(self, user_id: str) -> list[dict]:
        """Get all queued offline messages for user."""
        key = RedisKeys.offline_queue(user_id)
        messages = await self._redis.lrange(key, 0, -1)
        return [json.loads(msg) for msg in messages] if messages else []
    
    async def clear_offline_queue(self, user_id: str) -> None:
        """Clear offline queue after delivery."""
        key = RedisKeys.offline_queue(user_id)
        await self._redis.delete(key)
    
    async def get_online_users_from_list(self, user_ids: list[str]) -> tuple[list[str], list[str]]:
        """Partition users into online and offline lists."""
        online = []
        offline = []
        for user_id in user_ids:
            if await self.is_user_online(user_id):
                online.append(user_id)
            else:
                offline.append(user_id)
        return online, offline
