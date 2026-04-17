"""
AOS Redis Client
Session cache, real-time data, and event streaming.
"""

import redis.asyncio as redis

from app.core.config import get_settings

settings = get_settings()

redis_client = redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> redis.Redis:
    return redis_client


async def close_redis():
    await redis_client.close()
