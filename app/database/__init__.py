from contextlib import asynccontextmanager

import asyncpg
import redis
from fastapi import FastAPI

from app.utils.config import (
    db_connection_string, REDIS_PASSWORD, REDIS_USER,
    REDIS_HOST, REDIS_PORT, REDIS_DB
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for database and services initialization."""

    app.state.db_pool = await asyncpg.create_pool(
        db_connection_string,
        min_size=15, max_size=30,
    )

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

    yield

    print("Shutting down server...")

    await app.state.redis.close()
    await app.state.db_pool.close()

    print("HEX IAM shutdown complete")