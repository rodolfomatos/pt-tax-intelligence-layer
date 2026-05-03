"""
Rate limiting backends.

Provides pluggable backends for rate limiting:
- InMemoryBackend: original implementation (for testing)
- RedisBackend: production-ready using Redis sorted sets
"""

import time
import logging
import threading
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict
import redis.asyncio as redis
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitBackend(ABC):
    """Abstract backend interface."""

    @abstractmethod
    async def check_rate_limit(
        self, client_id: str, requests_per_minute: int, requests_per_hour: int, burst_limit: int
    ) -> Tuple[bool, Dict[str, str]]:
        """Check if client is within rate limits. Return (allowed, headers)."""
        pass

    @abstractmethod
    async def close(self):
        """Cleanup connections."""
        pass


class InMemoryBackend(RateLimitBackend):
    """Original in-memory rate limiter using sliding window."""

    def __init__(self):
        self._minute_cache: dict[str, list[float]] = {}
        self._hour_cache: dict[str, list[float]] = {}

    def _cleanup_old_entries(self, timestamps: list[float], max_age: float) -> list[float]:
        cutoff = time.time() - max_age
        return [ts for ts in timestamps if ts > cutoff]

    async def check_rate_limit(
        self, client_id: str, requests_per_minute: int, requests_per_hour: int, burst_limit: int
    ) -> Tuple[bool, Dict[str, str]]:
        now = time.time()

        minute_window = 60
        hour_window = 3600

        if client_id not in self._minute_cache:
            self._minute_cache[client_id] = []
        if client_id not in self._hour_cache:
            self._hour_cache[client_id] = []

        self._minute_cache[client_id] = self._cleanup_old_entries(
            self._minute_cache[client_id], minute_window
        )
        self._hour_cache[client_id] = self._cleanup_old_entries(
            self._hour_cache[client_id], hour_window
        )

        minute_count = len(self._minute_cache[client_id])
        hour_count = len(self._hour_cache[client_id])

        remaining_minute = requests_per_minute - minute_count
        remaining_hour = requests_per_hour - hour_count

        headers = {
            "X-RateLimit-Limit-Per-Minute": str(requests_per_minute),
            "X-RateLimit-Limit-Per-Hour": str(requests_per_hour),
            "X-RateLimit-Remaining-Per-Minute": str(max(0, remaining_minute)),
            "X-RateLimit-Remaining-Per-Hour": str(max(0, remaining_hour)),
            "X-RateLimit-Reset-Per-Minute": str(int(now + minute_window)),
            "X-RateLimit-Reset-Per-Hour": str(int(now + hour_window)),
        }

        if minute_count >= requests_per_minute:
            return False, headers
        if hour_count >= requests_per_hour:
            return False, headers
        if minute_count >= burst_limit and minute_count < requests_per_minute:
            return False, headers

        self._minute_cache[client_id].append(now)
        self._hour_cache[client_id].append(now)

        return True, headers

    async def close(self):
        """No resources to clean up."""
        pass


class RedisBackend(RateLimitBackend):
    """Redis-based rate limiter using sorted sets (sliding window)."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    async def check_rate_limit(
        self, client_id: str, requests_per_minute: int, requests_per_hour: int, burst_limit: int
    ) -> Tuple[bool, Dict[str, str]]:
        now = time.time()
        minute_key = f"ratelimit:minute:{client_id}"
        hour_key = f"ratelimit:hour:{client_id}"

        client = await self._get_client()

        # Use pipeline for atomic operations
        async with client.pipeline(transaction=True) as pipe:
            # Remove expired entries from minute window
            minute_cutoff = now - 60
            pipe.zremrangebyscore(minute_key, 0, minute_cutoff)
            # Count minute requests
            pipe.zcard(minute_key)
            # Remove expired entries from hour window
            hour_cutoff = now - 3600
            pipe.zremrangebyscore(hour_key, 0, hour_cutoff)
            # Count hour requests
            pipe.zcard(hour_key)
            # Execute
            _, minute_count, _, hour_count = await pipe.execute()

        minute_count = int(minute_count)
        hour_count = int(hour_count)

        remaining_minute = requests_per_minute - minute_count
        remaining_hour = requests_per_hour - hour_count

        headers = {
            "X-RateLimit-Limit-Per-Minute": str(requests_per_minute),
            "X-RateLimit-Limit-Per-Hour": str(requests_per_hour),
            "X-RateLimit-Remaining-Per-Minute": str(max(0, remaining_minute)),
            "X-RateLimit-Remaining-Per-Hour": str(max(0, remaining_hour)),
            "X-RateLimit-Reset-Per-Minute": str(int(now + 60)),
            "X-RateLimit-Reset-Per-Hour": str(int(now + 3600)),
        }

        if minute_count >= requests_per_minute:
            return False, headers
        if hour_count >= requests_per_hour:
            return False, headers
        if minute_count >= burst_limit and minute_count < requests_per_minute:
            return False, headers

        # Add current request to both windows
        async with client.pipeline(transaction=True) as pipe:
            pipe.zadd(minute_key, {str(now): now})
            pipe.zadd(hour_key, {str(now): now})
            # Set expiry on keys to auto-cleanup (safety)
            pipe.expire(minute_key, 120)  # 2 minutes
            pipe.expire(hour_key, 3700)   # 1 hour + margin
            await pipe.execute()

        return True, headers

    async def close(self):
        if self._client:
            await self._client.close()


_backend: Optional[RateLimitBackend] = None
_backend_lock = threading.Lock()


async def get_rate_limit_backend() -> RateLimitBackend:
    """Get configured rate limit backend (singleton)."""
    global _backend
    if _backend is None:
        with _backend_lock:
            if _backend is None:
                # Choose backend based on config
                if settings.rate_limit_backend == "redis":
                    if not settings.redis_url:
                        raise ValueError("REDIS_URL required when rate_limit_backend=redis")
                    _backend = RedisBackend(settings.redis_url)
                else:
                    _backend = InMemoryBackend()
    return _backend
