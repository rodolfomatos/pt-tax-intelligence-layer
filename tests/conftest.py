"""
Pytest configuration and fixtures for the PT Tax Intelligence Layer.
"""

import os
import pytest
from httpx import AsyncClient, ASGITransport
from app.models import TaxAnalysisInput, Context


def pytest_configure(config):
    """Set test environment variables before any app imports."""
    os.environ.setdefault("API_KEY", "test-api-key")
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/tax_intelligence")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("PTDATA_API_URL", "https://api.ptdata.org/mcp")
    os.environ.setdefault("PTDATA_API_KEY", "dummy")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("USE_IAEDU", "false")


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
