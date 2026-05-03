import json
import logging
import threading
from typing import Optional
from datetime import datetime, timezone
import redis.asyncio as redis
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheClient:
    """
    Redis cache for legislation and API responses.
    
    Supports:
    - TTL-based expiration (default)
    - Manual invalidation
    - Event-based invalidation (legal version changes)
    - Pattern-based bulk invalidation
    """
    
    def __init__(self, url: Optional[str] = None):
        self.url = url or settings.redis_url
        self._client: Optional[redis.Redis] = None
        self._version_key = "legal:version:current"
    
    async def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.url, decode_responses=True)
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.close()
    
    async def get(self, key: str) -> Optional[dict]:
        """Get value from cache."""
        try:
            client = await self._get_client()
            value = await client.get(key)
            if value:
                return json.loads(value)
        except redis.RedisError as e:
            logger.warning(f"Cache get failed: {e}")
        return None
    
    async def set(self, key: str, value: dict, ttl: Optional[int] = None):
        """Set value in cache."""
        try:
            client = await self._get_client()
            ttl = ttl or settings.cache_ttl_seconds
            await client.setex(key, ttl, json.dumps(value))
        except redis.RedisError as e:
            logger.warning(f"Cache set failed: {e}")
    
    async def delete(self, key: str):
        """Delete key from cache."""
        try:
            client = await self._get_client()
            await client.delete(key)
        except redis.RedisError as e:
            logger.warning(f"Cache delete failed: {e}")
    
    async def get_article(self, code: str, article: str) -> Optional[dict]:
        """Get cached article."""
        key = f"article:{code}:{article}"
        return await self.get(key)
    
    async def set_article(self, code: str, article: str, data: dict):
        """Cache article."""
        key = f"article:{code}:{article}"
        await self.set(key, data)
    
    async def search_legislation(self, query: str, code: Optional[str] = None) -> Optional[list]:
        """Get cached search results."""
        code_part = code or ""
        key = f"search:{query}:{code_part}"
        return await self.get(key)
    
    async def set_search_legislation(self, query: str, code: Optional[str], results: list):
        """Cache search results."""
        code_part = code or ""
        key = f"search:{query}:{code_part}"
        await self.set(key, results)
    
    async def health_check(self) -> bool:
        """Check if Redis is available."""
        try:
            client = await self._get_client()
            await client.ping()
            return True
        except redis.RedisError:
            return False
    
    async def invalidate_article(self, code: str, article: str):
        """Invalidate a specific article cache."""
        key = f"article:{code}:{article}"
        await self.delete(key)
        logger.info(f"Invalidated article cache: {code}/{article}")
    
    async def invalidate_search(self, query: str, code: Optional[str] = None):
        """Invalidate a specific search cache."""
        code_part = code or ""
        key = f"search:{query}:{code_part}"
        await self.delete(key)
        logger.info(f"Invalidated search cache: {query}")
    
    async def invalidate_by_pattern(self, pattern: str):
        """
        Invalidate all keys matching a pattern.
        
        Args:
            pattern: e.g., "article:CIVA:*" or "search:*"
        """
        try:
            client = await self._get_client()
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                if keys:
                    await client.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break
            logger.info(f"Invalidated {deleted} keys matching: {pattern}")
            return deleted
        except redis.RedisError as e:
            logger.warning(f"Pattern invalidation failed: {e}")
            return 0
    
    async def invalidate_legal_version(self, old_version: str, new_version: str):
        """
        Invalidate all cache when legal version changes.
        
        Called when ptdata API reports new legal version.
        """
        if old_version == new_version:
            return
        
        logger.info(f"Legal version changed: {old_version} -> {new_version}")
        
        await self.invalidate_by_pattern("article:*")
        await self.invalidate_by_pattern("search:*")
        
        await self.set(self._version_key, {"version": new_version, "updated": datetime.now(timezone.utc).isoformat()})
    
    async def get_legal_version(self) -> Optional[str]:
        """Get cached legal version."""
        data = await self.get(self._version_key)
        return data.get("version") if data else None
    
    async def invalidate_all(self):
        """Clear all cache (use with caution)."""
        try:
            client = await self._get_client()
            await client.flushdb()
            logger.warning("All cache cleared")
        except redis.RedisError as e:
            logger.warning(f"Cache clear failed: {e}")


_cache: Optional[CacheClient] = None
_cache_lock = threading.Lock()


async def get_cache_client() -> CacheClient:
    global _cache
    if _cache is None:
        with _cache_lock:
            if _cache is None:  # double-checked locking
                _cache = CacheClient()
    return _cache
