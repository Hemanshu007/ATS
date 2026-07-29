import structlog

from app.core.redis_client import get_redis

log = structlog.get_logger("ats.cache")

JOB_LIST_CACHE_PREFIX = "cache:jobs:list:"
JOB_LIST_CACHE_TTL_SECONDS = 60


def _job_list_cache_key(page: int, page_size: int, job_type: str | None, location: str | None) -> str:
    return f"{JOB_LIST_CACHE_PREFIX}{page}:{page_size}:{job_type or ''}:{location or ''}"


async def _cache_version_key() -> str:
    return f"{JOB_LIST_CACHE_PREFIX}_version"


async def _get_cache_version() -> int:
    r = await get_redis()
    v = await r.get(await _cache_version_key())
    return int(v) if v else 1


async def get_cached_job_list(page: int, page_size: int, job_type: str | None, location: str | None) -> dict | None:
    try:
        r = await get_redis()
        version = await _get_cache_version()
        key = _job_list_cache_key(version, page, page_size, job_type, location)
        cached = await r.get(key)
        if cached:
            import json
            log.debug("cache.hit", key=key)
            return json.loads(cached)
        log.debug("cache.miss", key=key)
        return None
    except Exception as e:
        log.warn("cache.read_failed", error=str(e))
        return None


async def set_cached_job_list(page: int, page_size: int, job_type: str | None, location: str | None, data: dict) -> None:
    try:
        r = await get_redis()
        version = await _get_cache_version()
        key = _job_list_cache_key(version, page, page_size, job_type, location)
        import json
        await r.set(key, json.dumps(data, default=str), ex=JOB_LIST_CACHE_TTL_SECONDS)
        log.debug("cache.set", key=key)
    except Exception as e:
        log.warn("cache.write_failed", error=str(e))


async def invalidate_job_list_cache() -> None:
    try:
        r = await get_redis()
        version_key = await _cache_version_key()
        await r.incr(version_key)
        log.debug("cache.invalidated")
    except Exception as e:
        log.warn("cache.invalidation_failed", error=str(e))
