"""
Development seeding script for creating test users.

Only runs when DEV_MODE=1 environment variable is set.
Creates 5 test users with predictable credentials for development/testing.
"""
import os
import logging
from uuid import uuid4

import bcrypt
from asyncpg import Connection
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEV_USERS = [
    {
        "username": "alice",
        "email": "alice@example.com",
        "password": "password123",
        "first_name": "Alice",
        "last_name": "Johnson",
        "role": "user"
    },
    {
        "username": "bob",
        "email": "bob@example.com",
        "password": "password123",
        "first_name": "Bob",
        "last_name": "Smith",
        "role": "user"
    },
    {
        "username": "charlie",
        "email": "charlie@example.com",
        "password": "password123",
        "first_name": "Charlie",
        "last_name": "Brown",
        "role": "user"
    },
    {
        "username": "diana",
        "email": "diana@example.com",
        "password": "password123",
        "first_name": "Diana",
        "last_name": "Prince",
        "role": "user"
    },
    {
        "username": "admin",
        "email": "admin@example.com",
        "password": "admin123",
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin"
    },
]


def _hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


async def seed_dev_users(db: Connection) -> dict:
    """
    Seed development users if DEV_MODE is enabled.
    
    Args:
        db: Database connection
        
    Returns:
        dict with seeding results
    """
    dev_mode = os.getenv("DEV_MODE", "0")
    if dev_mode != "1":
        return {"skipped": True, "reason": "DEV_MODE not enabled"}
    
    created = []
    skipped = []
    
    for user_data in DEV_USERS:
        existing = await db.fetchrow(
            "SELECT id FROM users WHERE username = $1 OR email = $2",
            user_data["username"], user_data["email"]
        )
        
        if existing:
            skipped.append(user_data["username"])
            continue
        
        user_id = uuid4()
        hashed_password = _hash_password(user_data["password"])
        
        await db.execute(
            """
            INSERT INTO users (id, username, email, password, first_name, last_name, role)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            user_id,
            user_data["username"],
            user_data["email"],
            hashed_password,
            user_data["first_name"],
            user_data["last_name"],
            user_data["role"]
        )
        created.append(user_data["username"])
        logger.info(f"Created dev user: {user_data['username']}")
    
    result = {
        "skipped": False,
        "created": created,
        "already_existed": skipped,
        "created_count": len(created)
    }
    
    if created:
        logger.info(f"Seeded {len(created)} dev user(s): {', '.join(created)}")
    if skipped:
        logger.info(f"Skipped {len(skipped)} existing user(s): {', '.join(skipped)}")
    
    return result
