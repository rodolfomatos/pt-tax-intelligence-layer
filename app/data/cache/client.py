import json
import logging
from typing import Optional
import redis.asyncio as redis
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheClient:
    """Redis cache for legislation and API responses."""
    
    def __init__(self, url: Optional[str] = None):
        self.url = url or settings.redis_url
        self._client: Optional[redis.Redis] = None
    
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


_cache: Optional[CacheClient] = None


async def get_cache_client() -> CacheClient:
    global _cache
    if _cache is None:
        _cache = CacheClient()
    return _cache
