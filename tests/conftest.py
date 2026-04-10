import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models import TaxAnalysisInput, Context


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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
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
        return {
            "code": "CIVA",
            "article": "20º",
            "title": "Deduções",
            "content": "Artigo completo...",
        }
    
    async def mock_health(*args, **kwargs):
        return True
    
    from app.data import ptdata
    monkeypatch.setattr(ptdata.client, "get_ptdata_client", lambda: MockPTData())


class MockPTData:
    async def search_legislation(self, *args, **kwargs):
        return [
            {"code": "CIVA", "article": "20º", "excerpt": "São dedutíveis..."}
        ]
    
    async def get_article(self, *args, **kwargs):
        return {"code": "CIVA", "article": "20º", "content": "..."}
    
    async def health_check(self, *args, **kwargs):
        return True
    
    async def close(self, *args, **kwargs):
        pass


@pytest.fixture
def mock_cache(monkeypatch):
    """Mock cache client for testing."""
    from app.data import cache
    monkeypatch.setattr(cache.client, "get_cache_client", lambda: MockCache())


class MockCache:
    async def search_legislation(self, *args, **kwargs):
        return None
    
    async def get_article(self, *args, **kwargs):
        return None
    
    async def health_check(self, *args, **kwargs):
        return True
    
    async def close(self, *args, **kwargs):
        pass
