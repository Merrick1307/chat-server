import time
import secrets
import hashlib
from typing import Optional
from uuid import UUID

import bcrypt
from asyncpg import Connection

from app.services.base import BaseService
from app.utils.logs import ErrorLogger
from app.utils.jwts import create_jwt_token
from app.utils.config import JWT_SECRET


class AuthService(BaseService):
    """
    Authentication service handling user signup, login, logout,
    and token management.
    """
    
    ACCESS_TOKEN_EXPIRY = 15 * 60  # 15 minutes
    REFRESH_TOKEN_EXPIRY = 7 * 24 * 60 * 60  # 7 days
    
    def __init__(self, db: Connection, logger: Optional[ErrorLogger] = None):
        super().__init__(db, logger)
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    
    @staticmethod
    def _verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    
    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash refresh token for storage."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
    
    async def _generate_tokens(self, user_id: UUID, email: str, username: str) -> dict:
        """Generate access and refresh tokens."""
        now = int(time.time())
        
        access_payload = {
            "sub": email,
            "user_id": str(user_id),
            "username": username,
            "iat": now,
            "exp": now + self.ACCESS_TOKEN_EXPIRY,
            "type": "access"
        }
        
        refresh_payload = {
            "sub": email,
            "user_id": str(user_id),
            "iat": now,
            "exp": now + self.REFRESH_TOKEN_EXPIRY,
            "type": "refresh",
            "jti": secrets.token_hex(16)
        }
        
        access_token = await create_jwt_token(access_payload, JWT_SECRET)
        refresh_token = await create_jwt_token(refresh_payload, JWT_SECRET)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.ACCESS_TOKEN_EXPIRY
        }
    
    async def signup(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str
    ) -> dict:
        """
        Register a new user.
        
        Returns:
            dict with user_id, access_token, refresh_token
        
        Raises:
            ValueError: If username or email already exists
        """
        existing = await self.db.fetchrow(
            "SELECT id FROM users WHERE username = $1 OR email = $2",
            username, email
        )
        if existing:
            raise ValueError("Username or email already exists")
        
        password_hash = self._hash_password(password)
        
        user = await self.db.fetchrow(
            """
            INSERT INTO users (username, email, password, first_name, last_name)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, username, email
            """,
            username, email, password_hash, first_name, last_name
        )
        
        user_id = user["id"]
        tokens = await self._generate_tokens(
            user_id, user["email"], user["username"]
        )
        
        token_hash = self._hash_token(tokens["refresh_token"])
        await self.db.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
            VALUES ($1, $2, NOW() + INTERVAL '7 days')
            """,
            user_id, token_hash
        )
        
        await self.log_info(f"User signed up: {username}")
        
        return {
            "user_id": str(user_id),
            **tokens
        }
    
    async def login(self, username: str, password: str) -> dict:
        """
        Authenticate user and return tokens.
        
        Returns:
            dict with user_id, access_token, refresh_token
        
        Raises:
            ValueError: If credentials are invalid
        """
        user = await self.db.fetchrow(
            """
            SELECT id, username, email, password
            FROM users
            WHERE username = $1 OR email = $1
            """,
            username
        )
        
        if not user:
            raise ValueError("Invalid credentials")
        
        if not self._verify_password(password, user["password"]):
            raise ValueError("Invalid credentials")
        
        tokens = await self._generate_tokens(
            user["id"], user["email"], user["username"]
        )
        
        token_hash = self._hash_token(tokens["refresh_token"])
        await self.db.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
            VALUES ($1, $2, NOW() + INTERVAL '7 days')
            """,
            user["id"], token_hash
        )
        
        await self.db.execute(
            "UPDATE users SET updated_at = NOW() WHERE id = $1",
            user["id"]
        )
        
        await self.log_info(f"User logged in: {user['username']}")
        
        return {
            "user_id": str(user["id"]),
            **tokens
        }
    
    async def logout(self, refresh_token: str) -> bool:
        """
        Invalidate refresh token.
        
        Returns:
            True if logout successful
        """
        token_hash = self._hash_token(refresh_token)
        
        result = await self.db.execute(
            """
            UPDATE refresh_tokens
            SET revoked = true
            WHERE token_hash = $1 AND revoked = false
            """,
            token_hash
        )
        
        await self.log_info("User logged out")
        return "UPDATE" in result
    
    async def refresh(self, refresh_token: str) -> dict:
        """
        Refresh access token using refresh token.
        
        Returns:
            dict with new access_token and refresh_token
        
        Raises:
            ValueError: If refresh token is invalid or expired
        """
        import jwt
        
        try:
            payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise ValueError("Refresh token expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid refresh token")
        
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        
        token_hash = self._hash_token(refresh_token)
        
        stored_token = await self.db.fetchrow(
            """
            SELECT rt.token_id, rt.user_id, u.username, u.email
            FROM refresh_tokens rt
            JOIN users u ON rt.user_id = u.id
            WHERE rt.token_hash = $1 
              AND rt.revoked = false 
              AND rt.expires_at > NOW()
            """,
            token_hash
        )
        
        if not stored_token:
            raise ValueError("Refresh token not found or revoked")
        
        await self.db.execute(
            "UPDATE refresh_tokens SET revoked = true WHERE token_id = $1",
            stored_token["token_id"]
        )
        
        tokens = await self._generate_tokens(
            stored_token["user_id"],
            stored_token["email"],
            stored_token["username"]
        )
        
        new_token_hash = self._hash_token(tokens["refresh_token"])
        await self.db.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
            VALUES ($1, $2, NOW() + INTERVAL '7 days')
            """,
            stored_token["user_id"], new_token_hash
        )
        
        await self.log_info(f"Token refreshed for user: {stored_token['username']}")
        
        return {
            "user_id": str(stored_token["user_id"]),
            **tokens
        }
    
    async def check_session(self, user_id: UUID) -> dict:
        """
        Verify user session is valid.
        
        Returns:
            dict with valid status and user info
        """
        user = await self.db.fetchrow(
            """
            SELECT id, username, email, created_at
            FROM users
            WHERE id = $1
            """,
            user_id
        )
        
        if not user:
            return {"valid": False}
        
        return {
            "valid": True,
            "user_id": str(user["id"]),
            "username": user["username"],
            "email": user["email"]
        }
    
    async def lookup_user(self, username: str) -> dict:
        """
        Look up a user by username.
        
        Returns:
            dict with user_id, username if found, None otherwise
        """
        user = await self.db.fetchrow(
            """
            SELECT id, username, first_name, last_name
            FROM users
            WHERE username = $1
            """,
            username
        )
        
        if not user:
            return None
        
        return {
            "user_id": str(user["id"]),
            "username": user["username"],
            "display_name": f"{user['first_name']} {user['last_name']}".strip() or user["username"]
        }
