import json

import structlog
from app.core.redis_client import redis_client

log = structlog.get_logger("ats.cache")

JOB_LIST_CACHE_PREFIX = "cache:jobs:list:"
JOB_LIST_CACHE_TTL_SECONDS = 60


def _job_list_cache_key(page: int, page_size: int, job_type: str | None, location: str | None) -> str:
    return f"{JOB_LIST_CACHE_PREFIX}{page}:{page_size}:{job_type or ''}:{location or ''}"


async def get_cached_job_list(page: int, page_size: int, job_type: str | None, location: str | None) -> dict | None:
    try:
        key = _job_list_cache_key(page, page_size, job_type, location)
        cached = await redis_client.get(key)
        if cached:
            log.debug("cache.hit", key=key)
            return json.loads(cached)
        log.debug("cache.miss", key=key)
        return None
    except Exception as e:
        log.warn("cache.read_failed", error=str(e))
        return None


async def set_cached_job_list(page: int, page_size: int, job_type: str | None, location: str | None, data: dict) -> None:
    try:
        key = _job_list_cache_key(page, page_size, job_type, location)
        await redis_client.set(key, json.dumps(data, default=str), ex=JOB_LIST_CACHE_TTL_SECONDS)
        log.debug("cache.set", key=key)
    except Exception as e:
        log.warn("cache.write_failed", error=str(e))


async def invalidate_job_list_cache() -> None:
    try:
        keys = await redis_client.keys(f"{JOB_LIST_CACHE_PREFIX}*")
        if keys:
            await redis_client.delete(*keys)
            log.debug("cache.invalidated", count=len(keys))
    except Exception as e:
        log.warn("cache.invalidation_failed", error=str(e))
