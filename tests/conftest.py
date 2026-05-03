"""
Pytest configuration and fixtures for the PT Tax Intelligence Layer.
"""

import os
import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from app.models import TaxAnalysisInput, Context

# Global to capture RateLimitMiddleware instance for cache clearing
_ratelimit_instance = None
_original_ratelimit_init = None


def _patched_ratelimit_init(self, app, requests_per_minute=60, requests_per_hour=1000, burst_limit=10):
    """Patch to capture the RateLimitMiddleware instance when it's created."""
    global _ratelimit_instance
    _ratelimit_instance = self
    _original_ratelimit_init(self, app, requests_per_minute, requests_per_hour, burst_limit)


def pytest_configure(config):
    """Set test environment variables before any app imports."""
    os.environ.setdefault("API_KEY", "test-api-key")
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/tax_intelligence")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("PTDATA_API_URL", "https://api.ptdata.org/mcp")
    os.environ.setdefault("PTDATA_API_KEY", "dummy")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("USE_IAEDU", "false")
    # Increase rate limits for test suite to avoid hitting limits
    os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "100000")
    os.environ.setdefault("RATE_LIMIT_PER_HOUR", "1000000")
    
    # Patch RateLimitMiddleware.__init__ to capture the instance for cache clearing
    global _original_ratelimit_init
    from app.middleware.rate_limit import RateLimitMiddleware
    _original_ratelimit_init = RateLimitMiddleware.__init__
    RateLimitMiddleware.__init__ = _patched_ratelimit_init


@pytest.fixture
def sample_expense_input():
    return TaxAnalysisInput(
        operation_type="expense",
        description="Alojamento em conferência internacional",
        amount=150.00,
        currency="EUR",
        entity_type="researcher",
        context=Context(
            project_type="FCT",
            activity_type="taxable",
            location="PT",
        ),
    )


@pytest.fixture
def sample_invoice_input():
    return TaxAnalysisInput(
        operation_type="invoice",
        description="Serviço de consultoria",
        amount=2500.00,
        currency="EUR",
        entity_type="department",
        context=Context(
            project_type="Horizon",
            activity_type="taxable",
            location="EU",
        ),
    )


@pytest.fixture
def sample_asset_input():
    return TaxAnalysisInput(
        operation_type="asset",
        description="Computador portátil",
        amount=800.00,
        currency="EUR",
        entity_type="department",
        context=Context(
            project_type="internal",
            activity_type="taxable",
            location="PT",
        ),
    )


@pytest.fixture
async def async_client():
    """Async client with test API key header."""
    from app.main import app
    transport = ASGITransport(app=app)
    headers = {"X-API-Key": "test-api-key"}
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=headers
    ) as client:
        yield client


@pytest.fixture
def mock_ptdata(monkeypatch):
    """Mock ptdata client for testing."""

    async def mock_search(*args, **kwargs):
        return [
            {
                "code": "CIVA",
                "article": "20º",
                "excerpt": "São dedutíveis as despesas...",
            }
        ]

    async def mock_get_article(*args, **kwargs):
        article = args[1] if len(args) > 1 else kwargs.get("article")
        if article == "999":
            return None
        return {
            "code": "CIVA",
            "article": "20º",
            "title": "Deduções",
            "content": "Artigo completo...",
        }

    async def mock_health(*args, **kwargs):
        return True

    async def mock_close(*args, **kwargs):
        pass

    class MockPTData:
        async def search_legislation(self, *args, **kwargs):
            return await mock_search(*args, **kwargs)

        async def get_article(self, *args, **kwargs):
            return await mock_get_article(*args, **kwargs)

        async def health_check(self, *args, **kwargs):
            return await mock_health()

        async def close(self, *args, **kwargs):
            await mock_close()

    import app.data.ptdata.client as ptdata_client_module
    monkeypatch.setattr(ptdata_client_module, "_client", MockPTData())
    monkeypatch.setattr(ptdata_client_module, "get_ptdata_client", lambda: MockPTData())

    from app.services.reasoning import LLMReasoning
    async def mock_analyze(self, input_data):
        return None
    monkeypatch.setattr(LLMReasoning, "analyze", mock_analyze)

    class MockMemoryLayers:
        def save_to_memory(self, *args, **kwargs): pass
        def get_l3_deep_search(self, *args, **kwargs): return []
    monkeypatch.setattr("app.data.memory.layers.get_memory_layers", lambda: MockMemoryLayers())

    class MockGraphBuilder:
        async def add_decision(self, *args, **kwargs): return "M1"
    monkeypatch.setattr("app.data.memory.graph.builder.get_graph_builder", lambda: MockGraphBuilder())


@pytest.fixture
def mock_cache(monkeypatch):
    """Mock cache client for testing."""
    import app.data.cache.client as cache_client_module

    class MockCache:
        async def search_legislation(self, *args, **kwargs):
            return None
        async def get_article(self, *args, **kwargs):
            return None
        async def health_check(self, *args, **kwargs):
            return True
        async def close(self, *args, **kwargs):
            pass

    monkeypatch.setattr(cache_client_module, "_cache", MockCache())


@pytest.fixture
def mock_graph_builder(monkeypatch):
    """Mock graph builder for testing."""
    from app.data.memory.graph.builder import KnowledgeGraphBuilder

    builder = AsyncMock(spec=KnowledgeGraphBuilder)
    builder.get_stats.return_value = {
        "total_nodes": 100,
        "total_edges": 200,
        "gmif_distribution": {"M1": 50, "M2": 30, "M3": 20}
    }
    builder.get_gmif_summary.return_value = builder.get_stats.return_value
    builder.get_decisions_by_gmif.return_value = []
    builder.find_contradictions.return_value = []

    # Patch the reference in the router module, not the original module
    monkeypatch.setattr(
        "app.routers.graph.get_graph_builder",
        lambda: builder
    )
    return builder


@pytest.fixture
def mock_audit_repo(monkeypatch):
    """Mock audit repository."""
    from app.database.audit import AuditRepository
    repo = AsyncMock(spec=AuditRepository)
    return repo


@pytest.fixture(autouse=True)
def reset_rate_limit_caches():
    """Clear rate limit caches before each test to avoid accumulation."""
    global _ratelimit_instance
    if _ratelimit_instance is not None:
        _ratelimit_instance._minute_cache.clear()
        _ratelimit_instance._hour_cache.clear()
