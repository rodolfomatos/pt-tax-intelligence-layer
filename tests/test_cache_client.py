"""
Tests for CacheClient.

Tests the Redis cache client.
"""

import pytest
from app.data.cache.client import CacheClient, get_cache_client


class MockRedis:
    """Mock Redis client with async methods."""
    def __init__(self):
        self.store = {}
        self.closed = False

    async def get(self, key):
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        self.store[key] = value

    async def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                count += 1
        return count

    async def ping(self):
        return True

    async def scan(self, cursor=0, match=None, count=100):
        # Simple pattern matching: support suffix '*'
        keys = []
        for k in self.store.keys():
            if match:
                if match.endswith('*'):
                    if k.startswith(match[:-1]):
                        keys.append(k)
                else:
                    if match in k:
                        keys.append(k)
            else:
                keys.append(k)
        return (0, keys)

    async def flushdb(self):
        self.store.clear()

    async def close(self):
        self.closed = True


@pytest.fixture
def redis_mock():
    """Create a fresh mock Redis."""
    return MockRedis()


@pytest.fixture
def cache_client(monkeypatch, redis_mock):
    """Create CacheClient with mocked _get_client."""
    async def _get_client(self):
        return redis_mock
    monkeypatch.setattr(CacheClient, "_get_client", _get_client)
    client = CacheClient()
    return client


@pytest.mark.asyncio
async def test_get_article(cache_client, redis_mock):
    """Should get article from cache."""
    redis_mock.store["article:CIVA:20º"] = '{"code":"CIVA","article":"20º"}'
    result = await cache_client.get_article("CIVA", "20º")
    assert result == {"code": "CIVA", "article": "20º"}


@pytest.mark.asyncio
async def test_set_article(cache_client, redis_mock):
    """Should set article in cache."""
    await cache_client.set_article("CIVA", "20º", {"code": "CIVA", "article": "20º"})
    assert "article:CIVA:20º" in redis_mock.store


@pytest.mark.asyncio
async def test_search_legislation(cache_client, redis_mock):
    """Should get cached search results."""
    redis_mock.store["search:test query:CIVA"] = '[{"code":"CIVA"}]'
    result = await cache_client.search_legislation("test query", code="CIVA")
    assert result == [{"code": "CIVA"}]


@pytest.mark.asyncio
async def test_set_search_legislation(cache_client, redis_mock):
    """Should set search results in cache."""
    await cache_client.set_search_legislation("test query", "CIVA", [{"code": "CIVA"}])
    assert "search:test query:CIVA" in redis_mock.store


@pytest.mark.asyncio
async def test_health_check(cache_client, redis_mock):
    """Should check health by pinging Redis."""
    healthy = await cache_client.health_check()
    assert healthy is True


@pytest.mark.asyncio
async def test_close(cache_client, redis_mock):
    """Should close client."""
    # Ensure _client is set
    cache_client._client = redis_mock
    await cache_client.close()
    assert redis_mock.closed is True


@pytest.mark.asyncio
async def test_invalidate_article(cache_client, redis_mock):
    """Should invalidate article cache."""
    redis_mock.store["article:CIVA:20º"] = '{"code":"CIVA"}'
    await cache_client.invalidate_article("CIVA", "20º")
    assert "article:CIVA:20º" not in redis_mock.store


@pytest.mark.asyncio
async def test_invalidate_search(cache_client, redis_mock):
    """Should invalidate search cache."""
    redis_mock.store["search:test:CIVA"] = '[]'
    await cache_client.invalidate_search("test", "CIVA")
    assert "search:test:CIVA" not in redis_mock.store


@pytest.mark.asyncio
async def test_invalidate_by_pattern(cache_client, redis_mock):
    """Should invalidate keys by pattern."""
    redis_mock.store["article:CIVA:20º"] = '{}'
    redis_mock.store["search:test:CIVA"] = '[]'
    deleted = await cache_client.invalidate_by_pattern("article:*")
    assert deleted == 1
    assert "article:CIVA:20º" not in redis_mock.store
    assert "search:test:CIVA" in redis_mock.store


@pytest.mark.asyncio
async def test_invalidate_all(cache_client, redis_mock):
    """Should clear all cache."""
    redis_mock.store["key1"] = "value1"
    await cache_client.invalidate_all()
    assert len(redis_mock.store) == 0


@pytest.mark.asyncio
async def test_get_handles_redis_error(monkeypatch):
    """Should handle RedisError gracefully and return None."""
    from app.data.cache.client import CacheClient
    import redis.asyncio as redis

    class FailingRedis:
        async def get(self, key):
            raise redis.RedisError("connection lost")
        async def setex(self, *args, **kwargs):
            pass  # not used
        async def delete(self, *keys):
            return 0
        async def ping(self):
            return True
        async def scan(self, *args, **kwargs):
            return (0, [])
        async def flushdb(self):
            pass
        async def close(self):
            pass

    async def _get_client(self):
        return FailingRedis()
    monkeypatch.setattr(CacheClient, "_get_client", _get_client)
    client = CacheClient()
    result = await client.get("key")
    assert result is None


@pytest.mark.asyncio
async def test_set_handles_redis_error(monkeypatch):
    """Should handle RedisError on set without raising."""
    from app.data.cache.client import CacheClient
    import redis.asyncio as redis

    class FailingRedis:
        async def setex(self, key, ttl, value):
            raise redis.RedisError("error")
        async def get(self, *args, **kwargs):
            pass
        async def delete(self, *keys):
            return 0
        async def ping(self):
            return True
        async def scan(self, *args, **kwargs):
            return (0, [])
        async def flushdb(self):
            pass
        async def close(self):
            pass

    async def _get_client(self):
        return FailingRedis()
    monkeypatch.setattr(CacheClient, "_get_client", _get_client)
    client = CacheClient()
    # Should not raise
    await client.set("key", {"a": 1}, ttl=60)


@pytest.mark.asyncio
async def test_get_cache_client_singleton(monkeypatch, redis_mock):
    """Should return singleton instance."""
    async def _get_client(self):
        return redis_mock
    monkeypatch.setattr(CacheClient, "_get_client", _get_client)
    # Reset global singleton
    import app.data.cache.client as cache_mod
    cache_mod._cache = None
    c1 = await get_cache_client()
    c2 = await get_cache_client()
    assert c1 is c2
