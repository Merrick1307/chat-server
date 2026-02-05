import logging
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
import redis.asyncio as redis
from fastapi import FastAPI
from yoyo import get_backend, read_migrations

from app.utils.config import (
    db_connection_string, REDIS_PASSWORD, REDIS_USER,
    REDIS_HOST, REDIS_PORT, REDIS_DB
)
from app.cache import WebSocketCacheService
from app.websocket import WebSocketManager
from app.database.seed import seed_dev_users

logger = logging.getLogger(__name__)

MIGRATIONS_PATH = Path(__file__).parent / "migrations"

def run_migrations(database_url: str, auto_apply: bool = True) -> dict:
    """
    Run database migrations using yoyo.

    Args:
        database_url: PostgreSQL connection string
        auto_apply: If True, automatically apply pending migrations

    Returns:
        dict with migration status
    """
    backend = get_backend(database_url)
    migrations = read_migrations(str(MIGRATIONS_PATH))

    pending = backend.to_apply(migrations)
    applied = backend.to_rollback(migrations)

    pending_list = list(pending)
    applied_list = list(applied)

    result = {
        "pending_count": len(pending_list),
        "applied_count": len(applied_list),
        "pending": [m.id for m in pending_list],
        "newly_applied": []
    }

    if pending_list and auto_apply:
        logger.info(f"Applying {len(pending_list)} pending migration(s)...")
        for migration in pending_list:
            logger.info(f"  → {migration.id}")

        try:
            backend.apply_migrations(backend.to_apply(migrations))
            result["newly_applied"] = [m.id for m in pending_list]
            logger.info("✓ Migrations applied successfully")
        except Exception as e:
            if "duplicate key" in str(e) or "UniqueViolation" in str(type(e).__name__):
                logger.info("✓ Migrations already applied by another worker")
            else:
                raise
    elif pending_list:
        logger.warning(f"{len(pending_list)} pending migrations not applied (auto_apply=False)")
    else:
        logger.info("✓ Database schema is up to date")

    backend.connection.close()
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for database and services initialization."""

    logger.info("Running database migrations...")
    try:
        migration_result = run_migrations(db_connection_string, auto_apply=True)
        if migration_result["newly_applied"]:
            logger.info(f"Applied migrations: {migration_result['newly_applied']}")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

    db_pool = await asyncpg.create_pool(
        db_connection_string,
        min_size=15, max_size=30,
    )

    # Seed using the pool variable directly
    async with db_pool.acquire() as conn:
        seed_result = await seed_dev_users(conn)
        if not seed_result.get("skipped"):
            logger.info(f"Dev seeding: {seed_result}")

    # Then assign to app.state
    app.state.db_pool = db_pool

    if REDIS_USER and REDIS_PASSWORD:
        REDIS_URL = f"redis://{REDIS_USER}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    elif REDIS_PASSWORD:
        REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    else:
        REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

    app.state.redis = redis.from_url(
        REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20
    )

    # Initialize WebSocket cache service and manager
    app.state.ws_cache = WebSocketCacheService(app.state.redis)
    app.state.ws_manager = WebSocketManager(app.state.redis, app.state.ws_cache)

    yield

    logger.info("Shutting down server...")

    await app.state.redis.aclose()
    await app.state.db_pool.close()

    logger.info("Chat server shutdown complete")
