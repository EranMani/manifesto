import redis.asyncio as redis

from app.core.config import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


async def cache_get(key: str) -> str | None:
    try:
        return await get_redis().get(key)
    except (redis.RedisError, ConnectionError):
        return None


async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    try:
        await get_redis().set(key, value, ex=ttl)
    except (redis.RedisError, ConnectionError):
        pass


async def cache_delete(key: str) -> None:
    try:
        await get_redis().delete(key)
    except (redis.RedisError, ConnectionError):
        pass
