import hashlib
from typing import Optional

from redis.asyncio import Redis

from app.cache.keys import RedisKeys


class TokenCacheService:
    """Service for managing password reset tokens in Redis."""
    
    def __init__(self, redis: Redis):
        self.redis = redis
    
    @staticmethod
    def hash_token(token: str) -> str:
        """Hash token for storage key."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def store_reset_token(self, token: str, user_id: str) -> None:
        """Store password reset token with TTL."""
        token_hash = self.hash_token(token)
        key = RedisKeys.password_reset_token(token_hash)
        await self.redis.setex(key, RedisKeys.PASSWORD_RESET_TTL, user_id)
    
    async def validate_reset_token(self, token: str) -> Optional[str]:
        """Validate token and return user_id if valid. Returns None if invalid/expired."""
        token_hash = self.hash_token(token)
        key = RedisKeys.password_reset_token(token_hash)
        user_id = await self.redis.get(key)
        return user_id if user_id else None
    
    async def invalidate_reset_token(self, token: str) -> bool:
        """Invalidate (delete) a reset token after use. Returns True if deleted."""
        token_hash = self.hash_token(token)
        key = RedisKeys.password_reset_token(token_hash)
        return await self.redis.delete(key) > 0
    
    async def get_all_reset_tokens(self) -> list[dict]:
        """Get all active reset tokens (for admin introspection)."""
        pattern = f"{RedisKeys.PASSWORD_RESET_PREFIX}*"
        tokens = []
        async for key in self.redis.scan_iter(match=pattern):
            ttl = await self.redis.ttl(key)
            user_id = await self.redis.get(key)
            if user_id:
                tokens.append({
                    "token_hash": key.replace(RedisKeys.PASSWORD_RESET_PREFIX, ""),
                    "user_id": user_id,
                    "ttl_seconds": ttl
                })
        return tokens
