"""Redis utilities for connection management and common operations."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as redis

from .settings import settings


@asynccontextmanager
async def redis_client() -> AsyncGenerator[redis.Redis, None]:
    """Context manager for Redis connections."""
    client = redis.from_url(str(settings.redis_uri))
    try:
        yield client
    finally:
        await client.aclose()


async def test_redis_connection() -> bool:
    """Test Redis connection."""
    try:
        async with redis_client() as client:
            await client.ping()
        return True
    except Exception:
        return False
