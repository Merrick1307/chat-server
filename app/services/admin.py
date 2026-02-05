from typing import Optional
from uuid import UUID

from asyncpg import Connection

from app.services.base import BaseService
from app.utils.logs import ErrorLogger


class AdminService(BaseService):
    """Service for admin-only operations."""
    
    def __init__(self, db: Connection, logger: Optional[ErrorLogger] = None):
        super().__init__(db, logger)
    
    async def get_all_users(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None
    ) -> dict:
        """Get all users with optional search."""
        if search:
            users = await self.db.fetch(
                """
                SELECT id::text, username, email, first_name, last_name, role, created_at, updated_at
                FROM users
                WHERE username ILIKE $1 OR email ILIKE $1 OR first_name ILIKE $1 OR last_name ILIKE $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                f"%{search}%", limit, offset
            )
            total = await self.db.fetchval(
                """
                SELECT COUNT(*) FROM users
                WHERE username ILIKE $1 OR email ILIKE $1 OR first_name ILIKE $1 OR last_name ILIKE $1
                """,
                f"%{search}%"
            )
        else:
            users = await self.db.fetch(
                """
                SELECT id::text, username, email, first_name, last_name, role, created_at, updated_at
                FROM users
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit, offset
            )
            total = await self.db.fetchval("SELECT COUNT(*) FROM users")
        
        return {
            "users": [dict(u) for u in users],
            "total": total,
            "has_more": offset + limit < total
        }
    
    async def get_user_detail(self, user_id: str) -> Optional[dict]:
        """Get detailed user information."""
        user = await self.db.fetchrow(
            """
            SELECT 
                id::text, username, email, first_name, last_name, role, 
                created_at, updated_at
            FROM users
            WHERE id = $1
            """,
            UUID(user_id)
        )
        
        if not user:
            return None
        
        message_count = await self.db.fetchval(
            "SELECT COUNT(*) FROM messages WHERE sender_id = $1",
            UUID(user_id)
        )
        
        group_count = await self.db.fetchval(
            "SELECT COUNT(*) FROM group_members WHERE user_id = $1",
            UUID(user_id)
        )
        
        return {
            **dict(user),
            "message_count": message_count,
            "group_count": group_count
        }
    
    async def delete_user(self, user_id: str, admin_id: str) -> bool:
        """Delete a user and their associated data."""
        if user_id == admin_id:
            raise ValueError("Cannot delete your own account")
        
        user = await self.db.fetchrow(
            "SELECT id, role FROM users WHERE id = $1",
            UUID(user_id)
        )
        
        if not user:
            raise ValueError("User not found")
        
        if user["role"] == "admin":
            raise ValueError("Cannot delete another admin")
        
        await self.db.execute(
            "DELETE FROM group_members WHERE user_id = $1",
            UUID(user_id)
        )
        await self.db.execute(
            "DELETE FROM refresh_tokens WHERE user_id = $1",
            UUID(user_id)
        )
        await self.db.execute(
            "DELETE FROM users WHERE id = $1",
            UUID(user_id)
        )
        
        await self.log_info(f"Admin {admin_id} deleted user {user_id}")
        return True
    
    async def update_user_role(self, user_id: str, new_role: str, admin_id: str) -> bool:
        """Update a user's role."""
        if user_id == admin_id:
            raise ValueError("Cannot change your own role")
        
        if new_role not in ("user", "admin"):
            raise ValueError("Invalid role. Must be 'user' or 'admin'")
        
        result = await self.db.execute(
            "UPDATE users SET role = $1, updated_at = NOW() WHERE id = $2",
            new_role, UUID(user_id)
        )
        
        await self.log_info(f"Admin {admin_id} changed role of {user_id} to {new_role}")
        return "UPDATE" in result
    
    async def get_all_groups(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        """Get all groups with member counts."""
        groups = await self.db.fetch(
            """
            SELECT 
                g.group_id::text as group_id,
                g.group_name,
                g.creator_id::text,
                g.created_at,
                COUNT(gm.user_id) as member_count
            FROM groups g
            LEFT JOIN group_members gm ON g.group_id = gm.group_id
            GROUP BY g.group_id, g.group_name, g.creator_id, g.created_at
            ORDER BY g.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        
        total = await self.db.fetchval("SELECT COUNT(*) FROM groups")
        
        return {
            "groups": [dict(g) for g in groups],
            "total": total,
            "has_more": offset + limit < total
        }
    
    async def delete_group(self, group_id: str, admin_id: str) -> bool:
        """Delete a group and its associated data."""
        group = await self.db.fetchrow(
            "SELECT group_id FROM groups WHERE group_id = $1",
            UUID(group_id)
        )
        
        if not group:
            raise ValueError("Group not found")
        
        await self.db.execute(
            "DELETE FROM group_message_reads WHERE group_id = $1",
            UUID(group_id)
        )
        await self.db.execute(
            "DELETE FROM group_messages WHERE group_id = $1",
            UUID(group_id)
        )
        await self.db.execute(
            "DELETE FROM group_members WHERE group_id = $1",
            UUID(group_id)
        )
        await self.db.execute(
            "DELETE FROM groups WHERE group_id = $1",
            UUID(group_id)
        )
        
        await self.log_info(f"Admin {admin_id} deleted group {group_id}")
        return True
    
    async def create_group(
        self,
        group_name: str,
        creator_id: str,
        member_ids: list[str]
    ) -> dict:
        """Create a new group as admin."""
        from uuid import uuid4
        
        group_id = uuid4()
        
        await self.db.execute(
            """
            INSERT INTO groups (group_id, group_name, creator_id)
            VALUES ($1, $2, $3)
            """,
            group_id, group_name, UUID(creator_id)
        )
        
        await self.db.execute(
            """
            INSERT INTO group_members (group_id, user_id, role)
            VALUES ($1, $2, 'admin')
            """,
            group_id, UUID(creator_id)
        )
        
        for member_id in member_ids:
            if member_id != creator_id:
                await self.db.execute(
                    """
                    INSERT INTO group_members (group_id, user_id, role)
                    VALUES ($1, $2, 'member')
                    ON CONFLICT DO NOTHING
                    """,
                    group_id, UUID(member_id)
                )
        
        await self.log_info(f"Admin {creator_id} created group {group_id}")
        
        return {
            "group_id": str(group_id),
            "group_name": group_name,
            "member_count": len(member_ids) + 1
        }
    
    async def get_group_detail(self, group_id: str) -> Optional[dict]:
        """Get detailed group information including members."""
        group = await self.db.fetchrow(
            """
            SELECT 
                g.group_id::text as group_id,
                g.group_name,
                g.creator_id::text,
                g.created_at,
                u.username as creator_username
            FROM groups g
            JOIN users u ON g.creator_id = u.id
            WHERE g.group_id = $1
            """,
            UUID(group_id)
        )
        
        if not group:
            return None
        
        members = await self.db.fetch(
            """
            SELECT 
                u.id::text as user_id,
                u.username,
                u.first_name,
                u.last_name,
                gm.role,
                gm.joined_at
            FROM group_members gm
            JOIN users u ON gm.user_id = u.id
            WHERE gm.group_id = $1
            ORDER BY gm.joined_at
            """,
            UUID(group_id)
        )
        
        message_count = await self.db.fetchval(
            "SELECT COUNT(*) FROM group_messages WHERE group_id = $1",
            UUID(group_id)
        )
        
        return {
            **dict(group),
            "members": [dict(m) for m in members],
            "member_count": len(members),
            "message_count": message_count
        }
