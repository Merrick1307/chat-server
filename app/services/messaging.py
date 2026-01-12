from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone

from asyncpg import Connection

from app.services.base import BaseService
from app.utils.logs import ErrorLogger


class MessageService(BaseService):
    """Service for handling direct message operations."""
    
    def __init__(self, db: Connection, logger: Optional[ErrorLogger] = None):
        super().__init__(db, logger)
    
    async def save_direct_message(
        self,
        message_id: str,
        sender_id: str,
        recipient_id: str,
        content: str,
        message_type: str = "text",
        delivered_at: Optional[str] = None
    ) -> Optional[dict]:
        """Save a direct message to the database."""
        query = """
            INSERT INTO messages (message_id, sender_id, recipient_id, content, message_type, delivered_at)
            VALUES ($1::uuid, $2::uuid, $3::uuid, $4, $5, $6)
            RETURNING message_id, sender_id, recipient_id, content, message_type, created_at, delivered_at
        """
        delivered_ts = None
        if delivered_at:
            delivered_ts = datetime.fromisoformat(delivered_at.replace('Z', '+00:00'))
        
        row = await self.db.fetchrow(
            query, message_id, sender_id, recipient_id, content, message_type, delivered_ts
        )
        
        if row:
            return dict(row)
        return None
    
    async def get_message(self, message_id: str) -> Optional[dict]:
        """Get a message by ID."""
        query = """
            SELECT message_id::text AS message_id, sender_id::text AS sender_id, 
                   recipient_id::text AS recipient_id, content, message_type,
                   created_at, delivered_at, read_at
            FROM messages WHERE message_id = $1::uuid
        """
        row = await self.db.fetchrow(query, message_id)
        return dict(row) if row else None
    
    async def get_conversation(
        self,
        user1_id: str,
        user2_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """Get conversation between two users."""
        query = """
            SELECT m.message_id::text AS message_id, m.sender_id::text AS sender_id, 
                   m.recipient_id::text AS recipient_id, m.content, m.message_type,
                   m.created_at, m.delivered_at, m.read_at,
                   u.username AS sender_username
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE (m.sender_id = $1::uuid AND m.recipient_id = $2::uuid)
               OR (m.sender_id = $2::uuid AND m.recipient_id = $1::uuid)
            ORDER BY m.created_at ASC
            LIMIT $3 OFFSET $4
        """
        rows = await self.db.fetch(query, user1_id, user2_id, limit, offset)
        return [dict(row) for row in rows]
    
    async def get_conversation_count(self, user1_id: str, user2_id: str) -> int:
        """Get total message count in a conversation."""
        query = """
            SELECT COUNT(*) FROM messages
            WHERE (sender_id = $1::uuid AND recipient_id = $2::uuid)
               OR (sender_id = $2::uuid AND recipient_id = $1::uuid)
        """
        result = await self.db.fetchval(query, user1_id, user2_id)
        return result or 0
    
    async def get_unread_messages(self, user_id: str) -> List[dict]:
        """Get unread messages for a user."""
        query = """
            SELECT m.message_id::text AS message_id, m.sender_id::text AS sender_id, 
                   m.recipient_id::text AS recipient_id, m.content, m.message_type,
                   m.created_at, m.delivered_at, m.read_at,
                   u.username AS sender_username,
                   COALESCE(NULLIF(TRIM(u.first_name || ' ' || u.last_name), ''), u.username) AS sender_display_name
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.recipient_id = $1::uuid AND m.read_at IS NULL
            ORDER BY m.created_at DESC
        """
        rows = await self.db.fetch(query, user_id)
        return [dict(row) for row in rows]
    
    async def mark_as_delivered(self, message_id: str) -> bool:
        """Mark a message as delivered."""
        query = """
            UPDATE messages SET delivered_at = NOW()
            WHERE message_id = $1::uuid AND delivered_at IS NULL
            RETURNING message_id
        """
        result = await self.db.fetchval(query, message_id)
        return result is not None
    
    async def mark_as_read(self, message_id: str, user_id: str) -> bool:
        """Mark a message as read."""
        query = """
            UPDATE messages SET read_at = NOW()
            WHERE message_id = $1::uuid AND recipient_id = $2::uuid AND read_at IS NULL
            RETURNING message_id
        """
        result = await self.db.fetchval(query, message_id, user_id)
        return result is not None
    
    async def get_username_by_id(self, user_id: str) -> Optional[str]:
        """Get username by user ID."""
        query = "SELECT username FROM users WHERE id = $1::uuid"
        result = await self.db.fetchval(query, user_id)
        return result
    
    async def get_conversations_list(self, user_id: str) -> List[dict]:
        """Get list of all conversation partners with last message and unread count."""
        query = """
            WITH conversation_partners AS (
                SELECT DISTINCT
                    CASE 
                        WHEN sender_id = $1::uuid THEN recipient_id
                        ELSE sender_id
                    END AS partner_id
                FROM messages
                WHERE sender_id = $1::uuid OR recipient_id = $1::uuid
            ),
            last_messages AS (
                SELECT DISTINCT ON (partner_id)
                    cp.partner_id,
                    m.message_id,
                    m.content,
                    m.created_at,
                    m.sender_id
                FROM conversation_partners cp
                JOIN messages m ON (
                    (m.sender_id = $1::uuid AND m.recipient_id = cp.partner_id)
                    OR (m.sender_id = cp.partner_id AND m.recipient_id = $1::uuid)
                )
                ORDER BY cp.partner_id, m.created_at DESC
            ),
            unread_counts AS (
                SELECT 
                    sender_id AS partner_id,
                    COUNT(*) AS unread_count
                FROM messages
                WHERE recipient_id = $1::uuid AND read_at IS NULL
                GROUP BY sender_id
            )
            SELECT 
                lm.partner_id::text AS partner_id,
                u.username,
                COALESCE(NULLIF(TRIM(u.first_name || ' ' || u.last_name), ''), u.username) AS display_name,
                lm.content AS last_message,
                lm.created_at AS last_message_at,
                lm.sender_id::text AS last_message_sender_id,
                COALESCE(uc.unread_count, 0) AS unread_count
            FROM last_messages lm
            JOIN users u ON lm.partner_id = u.id
            LEFT JOIN unread_counts uc ON lm.partner_id = uc.partner_id
            ORDER BY lm.created_at DESC
        """
        rows = await self.db.fetch(query, user_id)
        return [dict(row) for row in rows]
    
    async def get_message_sender(self, message_id: str) -> Optional[str]:
        """Get the sender_id for a message."""
        query = "SELECT sender_id::text FROM messages WHERE message_id = $1::uuid"
        result = await self.db.fetchval(query, message_id)
        return result


class GroupService(BaseService):
    """Service for handling group operations."""
    
    def __init__(self, db: Connection, logger: Optional[ErrorLogger] = None):
        super().__init__(db, logger)
    
    async def create_group(
        self,
        creator_id: str,
        group_name: str,
        member_ids: List[str]
    ) -> Optional[dict]:
        """Create a new group with initial members."""
        # Create the group
        create_query = """
            INSERT INTO groups (group_name, creator_id)
            VALUES ($1, $2::uuid)
            RETURNING group_id, group_name, creator_id, created_at
        """
        group_row = await self.db.fetchrow(create_query, group_name, creator_id)
        
        if not group_row:
            return None
        
        group_id = str(group_row['group_id'])
        
        # Add creator as admin
        await self._add_member(group_id, creator_id, "admin")
        
        # Add other members
        for member_id in member_ids:
            if member_id != creator_id:
                await self._add_member(group_id, member_id, "member")
        
        return dict(group_row)
    
    async def _add_member(self, group_id: str, user_id: str, role: str = "member") -> bool:
        """Add a member to a group."""
        query = """
            INSERT INTO group_members (group_id, user_id, role)
            VALUES ($1::uuid, $2::uuid, $3)
            ON CONFLICT (group_id, user_id) DO NOTHING
            RETURNING user_id
        """
        result = await self.db.fetchval(query, group_id, user_id, role)
        return result is not None
    
    async def add_members(self, group_id: str, user_ids: List[str]) -> int:
        """Add multiple members to a group. Returns count added."""
        added = 0
        for user_id in user_ids:
            if await self._add_member(group_id, user_id):
                added += 1
        return added
    
    async def remove_member(self, group_id: str, user_id: str) -> bool:
        """Remove a member from a group."""
        query = """
            DELETE FROM group_members
            WHERE group_id = $1::uuid AND user_id = $2::uuid
            RETURNING user_id
        """
        result = await self.db.fetchval(query, group_id, user_id)
        return result is not None
    
    async def get_group(self, group_id: str) -> Optional[dict]:
        """Get group details."""
        query = """
            SELECT g.group_id, g.group_name, g.creator_id, g.created_at,
                   COUNT(gm.user_id) as member_count
            FROM groups g
            LEFT JOIN group_members gm ON g.group_id = gm.group_id
            WHERE g.group_id = $1::uuid
            GROUP BY g.group_id
        """
        row = await self.db.fetchrow(query, group_id)
        return dict(row) if row else None
    
    async def get_group_members(self, group_id: str) -> List[str]:
        """Get list of group member IDs."""
        query = "SELECT user_id::text FROM group_members WHERE group_id = $1::uuid"
        rows = await self.db.fetch(query, group_id)
        return [row['user_id'] for row in rows]
    
    async def get_group_members_detail(self, group_id: str) -> List[dict]:
        """Get detailed group member info."""
        query = """
            SELECT gm.user_id, u.username, gm.role, gm.joined_at
            FROM group_members gm
            JOIN users u ON gm.user_id = u.id
            WHERE gm.group_id = $1::uuid
            ORDER BY gm.joined_at
        """
        rows = await self.db.fetch(query, group_id)
        return [dict(row) for row in rows]
    
    async def get_user_groups(self, user_id: str) -> List[dict]:
        """Get all groups a user belongs to."""
        query = """
            SELECT g.group_id, g.group_name, g.creator_id, g.created_at,
                   gm.role, gm.joined_at,
                   (SELECT COUNT(*) FROM group_members WHERE group_id = g.group_id) as member_count
            FROM groups g
            JOIN group_members gm ON g.group_id = gm.group_id
            WHERE gm.user_id = $1::uuid
            ORDER BY g.created_at DESC
        """
        rows = await self.db.fetch(query, user_id)
        return [dict(row) for row in rows]
    
    async def is_member(self, group_id: str, user_id: str) -> bool:
        """Check if user is a member of the group."""
        query = """
            SELECT 1 FROM group_members
            WHERE group_id = $1::uuid AND user_id = $2::uuid
        """
        result = await self.db.fetchval(query, group_id, user_id)
        return result is not None
    
    async def get_member_role(self, group_id: str, user_id: str) -> Optional[str]:
        """Get a member's role in the group."""
        query = """
            SELECT role FROM group_members
            WHERE group_id = $1::uuid AND user_id = $2::uuid
        """
        return await self.db.fetchval(query, group_id, user_id)


class GroupMessageService(BaseService):
    """Service for handling group message operations."""
    
    def __init__(self, db: Connection, logger: Optional[ErrorLogger] = None):
        super().__init__(db, logger)
    
    async def save_group_message(
        self,
        message_id: str,
        group_id: str,
        sender_id: str,
        content: str,
        message_type: str = "text"
    ) -> Optional[dict]:
        """Save a group message to the database."""
        query = """
            INSERT INTO group_messages (message_id, group_id, sender_id, content, message_type)
            VALUES ($1::uuid, $2::uuid, $3::uuid, $4, $5)
            RETURNING message_id, group_id, sender_id, content, message_type, created_at
        """
        row = await self.db.fetchrow(
            query, message_id, group_id, sender_id, content, message_type
        )
        return dict(row) if row else None
    
    async def get_group_message(self, message_id: str) -> Optional[dict]:
        """Get a group message by ID."""
        query = """
            SELECT message_id::text AS message_id, group_id::text AS group_id, 
                   sender_id::text AS sender_id, content, message_type, created_at
            FROM group_messages WHERE message_id = $1::uuid
        """
        row = await self.db.fetchrow(query, message_id)
        return dict(row) if row else None
    
    async def get_group_messages(
        self,
        group_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """Get messages for a group."""
        query = """
            SELECT gm.message_id::text AS message_id, gm.group_id::text AS group_id, 
                   gm.sender_id::text AS sender_id, gm.content,
                   gm.message_type, gm.created_at, u.username as sender_username
            FROM group_messages gm
            JOIN users u ON gm.sender_id = u.id
            WHERE gm.group_id = $1::uuid
            ORDER BY gm.created_at ASC
            LIMIT $2 OFFSET $3
        """
        rows = await self.db.fetch(query, group_id, limit, offset)
        return [dict(row) for row in rows]
    
    async def get_group_message_count(self, group_id: str) -> int:
        """Get total message count in a group."""
        query = "SELECT COUNT(*) FROM group_messages WHERE group_id = $1::uuid"
        result = await self.db.fetchval(query, group_id)
        return result or 0
    
    async def mark_group_message_read(self, message_id: str, user_id: str) -> bool:
        """Mark a group message as read by a user."""
        query = """
            INSERT INTO group_message_reads (message_id, user_id)
            VALUES ($1::uuid, $2::uuid)
            ON CONFLICT (message_id, user_id) DO NOTHING
            RETURNING message_id
        """
        result = await self.db.fetchval(query, message_id, user_id)
        return result is not None
    
    async def get_unread_group_messages(self, group_id: str, user_id: str) -> List[dict]:
        """Get unread group messages for a user."""
        query = """
            SELECT gm.message_id::text AS message_id, gm.group_id::text AS group_id, 
                   gm.sender_id::text AS sender_id, gm.content,
                   gm.message_type, gm.created_at
            FROM group_messages gm
            LEFT JOIN group_message_reads gmr 
                ON gm.message_id = gmr.message_id AND gmr.user_id = $2::uuid
            WHERE gm.group_id = $1::uuid 
                AND gm.sender_id != $2::uuid
                AND gmr.message_id IS NULL
            ORDER BY gm.created_at ASC
        """
        rows = await self.db.fetch(query, group_id, user_id)
        return [dict(row) for row in rows]
