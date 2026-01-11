class RedisKeys:
    """Redis key patterns for the chat application."""
    
    # Key prefixes
    ONLINE_PREFIX = "online:"
    OFFLINE_QUEUE_PREFIX = "offline_queue:"
    WS_CONNECTIONS_KEY = "ws_connections"
    TYPING_PREFIX = "typing:"
    
    # TTL values (in seconds)
    ONLINE_TTL = 300  # 5 minutes
    OFFLINE_QUEUE_TTL = 2592000  # 30 days
    TYPING_TTL = 5  # 5 seconds
    
    @staticmethod
    def user_online(user_id: str) -> str:
        """Key for tracking user online status."""
        return f"{RedisKeys.ONLINE_PREFIX}{user_id}"
    
    @staticmethod
    def offline_queue(user_id: str) -> str:
        """Key for user's offline message queue."""
        return f"{RedisKeys.OFFLINE_QUEUE_PREFIX}{user_id}"
    
    @staticmethod
    def typing_indicator(user_id: str, recipient_id: str) -> str:
        """Key for typing indicator between users."""
        return f"{RedisKeys.TYPING_PREFIX}{user_id}:{recipient_id}"
    
    @staticmethod
    def ws_connections() -> str:
        """Key for WebSocket connections hash."""
        return RedisKeys.WS_CONNECTIONS_KEY
