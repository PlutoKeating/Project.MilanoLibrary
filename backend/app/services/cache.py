import os
from typing import Optional
from app.config import settings

redis_client = None


def _get_redis():
    global redis_client
    if redis_client is not None:
        return redis_client

    # Try standard redis first
    if settings.redis_url:
        import redis as redis_lib

        redis_client = redis_lib.from_url(settings.redis_url, decode_responses=True)
        return redis_client

    # Try Upstash REST
    if settings.upstash_redis_rest_url and settings.upstash_redis_rest_token:
        try:
            from upstash_redis import Redis

            redis_client = Redis(
                url=settings.upstash_redis_rest_url,
                token=settings.upstash_redis_rest_token,
            )
            return redis_client
        except ImportError:
            pass

    return None


def get_cache_id(video_config: dict) -> str:
    show_timestamp = video_config.get("show_timestamp", False)
    video_id = video_config.get("video_id", "")
    page_number = video_config.get("page_number")
    output_language = video_config.get("output_language", "zh")
    model = video_config.get("model", "")

    prefix = "timestamp-" if show_timestamp else ""
    page_suffix = f"-p{page_number}" if page_number else ""
    normalized_model = (model or "default").replace(r"[^\w.-]", "_")
    return f"{prefix}{video_id}{page_suffix}-{output_language}-{normalized_model}"


async def get_cached_result(cache_id: str) -> Optional[str]:
    r = _get_redis()
    if not r:
        return None
    try:
        return r.get(cache_id)
    except Exception:
        return None


async def set_cached_result(cache_id: str, value: str):
    r = _get_redis()
    if not r:
        return
    try:
        r.set(cache_id, value)
        r.sadd("milanolibrary:cache_keys", cache_id)
    except Exception:
        pass


async def clear_all_cache():
    r = _get_redis()
    if not r:
        return {"success": True, "deleted": 0, "message": "No Redis configured"}
    try:
        keys = r.smembers("milanolibrary:cache_keys")
        if keys:
            for key in keys:
                r.delete(key)
            r.delete("milanolibrary:cache_keys")
            return {"success": True, "deleted": len(keys)}
        return {"success": True, "deleted": 0, "message": "No cached keys found"}
    except Exception as e:
        return {"success": False, "error": str(e)}
