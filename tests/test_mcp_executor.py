"""
Tests for MCPToolExecutor.

Tests the MCP tool executor with mocked dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.data.mcp.executor import MCPToolExecutor


@pytest.fixture
def mock_ptdata(monkeypatch):
    """Mock ptdata client."""
    mock = AsyncMock()
    mock.search_legislation = AsyncMock(return_value=[{"code": "CIVA", "article": "20º"}])
    mock.search_jurisprudence = AsyncMock(return_value=[])
    mock.get_tax_rulings = AsyncMock(return_value=[])
    mock.get_official_interpretations = AsyncMock(return_value=[])
    mock.get_article = AsyncMock(return_value={"code": "CIVA", "article": "20º", "excerpt": "Test"})
    mock.search_decisions = AsyncMock(return_value=[])
    monkeypatch.setattr("app.data.mcp.executor.get_ptdata_client", AsyncMock(return_value=mock))
    return mock


@pytest.fixture
def mock_cache(monkeypatch):
    """Mock cache client."""
    mock = AsyncMock()
    mock.search_legislation = AsyncMock(return_value=None)  # cache miss
    mock.set_search_legislation = AsyncMock()
    mock.get_article = AsyncMock(return_value=None)
    mock.set_article = AsyncMock()
    monkeypatch.setattr("app.data.mcp.executor.get_cache_client", AsyncMock(return_value=mock))
    return mock


@pytest.fixture
def mock_audit(monkeypatch):
    """Mock audit repository."""
    from app.database.audit import AuditRepository
    repo = AsyncMock(spec=AuditRepository)
    repo.get_decisions = AsyncMock(return_value=[
        MagicMock(id="123", description="Expense report", decision="deductible", confidence=0.9)
    ])
    monkeypatch.setattr("app.data.mcp.executor.get_audit_repository", lambda: repo)
    return repo


@pytest.mark.asyncio
async def test_execute_unknown_tool():
    """Should return error for unknown tool."""
    executor = MCPToolExecutor()
    result = await executor.execute("unknown", {})
    assert "error" in result
    assert "Unknown tool" in result["error"]


@pytest.mark.asyncio
async def test_search_legislation_cache_miss(mock_ptdata, mock_cache):
    """Should fetch from ptdata and cache results."""
    executor = MCPToolExecutor()
    result = await executor.execute("search_legislation", {"query": "test", "limit": 5})
    assert "results" in result
    assert result["cached"] is False
    assert len(result["results"]) == 1
    mock_ptdata.search_legislation.assert_called_once()
    mock_cache.set_search_legislation.assert_called_once()


@pytest.mark.asyncio
async def test_search_legislation_cache_hit(mock_ptdata, mock_cache):
    """Should return cached results if available."""
    mock_cache.search_legislation.return_value = [{"code": "CIVA"}]
    executor = MCPToolExecutor()
    result = await executor.execute("search_legislation", {"query": "test"})
    assert result["cached"] is True
    assert len(result["results"]) == 1
    mock_ptdata.search_legislation.assert_not_called()


@pytest.mark.asyncio
async def test_get_article(mock_ptdata, mock_cache):
    """Should get article via cache/ptdata."""
    executor = MCPToolExecutor()
    result = await executor.execute("get_article", {"code": "CIVA", "article": "20º"})
    assert "article" in result
    assert result["article"]["code"] == "CIVA"


@pytest.mark.asyncio
async def test_search_decisions(mock_audit):
    """Should search decisions."""
    executor = MCPToolExecutor()
    result = await executor.execute("search_decisions", {"query": "expense"})
    assert "results" in result
    assert len(result["results"]) == 1


@pytest.mark.asyncio
async def test_search_jurisprudence(mock_ptdata, mock_cache):
    """Should search jurisprudence."""
    mock_ptdata.search_jurisprudence.return_value = [{"court": "Supreme"}]
    executor = MCPToolExecutor()
    result = await executor.execute("search_jurisprudence", {"query": "tax"})
    assert len(result["results"]) == 1


@pytest.mark.asyncio
async def test_get_tax_rulings(mock_ptdata, mock_cache):
    """Should get tax rulings."""
    mock_ptdata.get_tax_rulings.return_value = [{"code": "CIVA", "topic": "deductions"}]
    executor = MCPToolExecutor()
    result = await executor.execute("get_tax_rulings", {"code": "CIVA"})
    assert len(result["results"]) == 1


@pytest.mark.asyncio
async def test_get_official_interpretations(mock_ptdata, mock_cache):
    """Should get official interpretations."""
    mock_ptdata.get_official_interpretations.return_value = [{"subject": "VAT"}]
    executor = MCPToolExecutor()
    result = await executor.execute("get_official_interpretations", {"code": "CIVA"})
    assert len(result["results"]) == 1


@pytest.mark.asyncio
async def test_tool_error_handling(mock_ptdata, mock_cache):
    """Should return error if executor raises."""
    mock_ptdata.search_legislation.side_effect = Exception("Network error")
    executor = MCPToolExecutor()
    result = await executor.execute("search_legislation", {"query": "test"})
    assert "error" in result
    assert "Network error" in result["error"]
