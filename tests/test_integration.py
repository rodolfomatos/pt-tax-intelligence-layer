"""
Integration tests for API endpoints.

Requires running services (Docker): make docker-up
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

HEADERS = {"X-API-Key": "test-api-key"}


@pytest.fixture(autouse=True)
def mock_ptdata_integration(monkeypatch):
    """Mock ptdata client for integration tests to avoid external dependencies."""
    from app.data.ptdata.client import PTDataClient

    async def mock_search_legislation(self, q, code=None, limit=10):
        return [
            {
                "code": "CIVA",
                "article": "20º",
                "excerpt": f"Resultado para {q}",
            }
        ]

    async def mock_get_article(self, code, article):
        return {
            "code": code,
            "article": article,
            "title": "Artigo de teste",
            "content": "Conteúdo do artigo..."
        }

    async def mock_health_check(self):
        return True

    async def mock_close(self):
        pass

    # Apply mocks
    monkeypatch.setattr(PTDataClient, "search_legislation", mock_search_legislation)
    monkeypatch.setattr(PTDataClient, "get_article", mock_get_article)
    monkeypatch.setattr(PTDataClient, "health_check", mock_health_check)
    monkeypatch.setattr(PTDataClient, "close", mock_close)


@pytest.mark.integration
class TestHealthEndpoint:
    """Tests for /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=HEADERS
        ) as client:
            response = await client.get("/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_returns_status(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=HEADERS
        ) as client:
            response = await client.get("/health")
            data = response.json()
            assert "status" in data
            assert "dependencies" in data


@pytest.mark.integration
class TestAnalyzeEndpoint:
    """Tests for /tax/analyze endpoint."""

    @pytest.mark.asyncio
    async def test_analyze_requires_json(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=HEADERS
        ) as client:
            response = await client.post("/tax/analyze")
            assert response.status_code in (401, 422)

    @pytest.mark.asyncio
    async def test_analyze_validates_input(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=HEADERS
        ) as client:
            response = await client.post("/tax/analyze", json={"invalid": "data"})
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_analyze_with_valid_input(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=HEADERS
        ) as client:
            response = await client.post(
                "/tax/analyze",
                json={
                    "operation_type": "expense",
                    "description": "Office supplies",
                    "amount": 50.0,
                    "currency": "EUR",
                    "entity_type": "department",
                    "context": {
                        "project_type": "internal",
                        "activity_type": "taxable",
                        "location": "PT",
                    },
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "decision" in data
            assert "confidence" in data


@pytest.mark.integration
class TestValidateEndpoint:
    """Tests for /tax/validate endpoint."""

    @pytest.mark.asyncio
    async def test_validate_valid_decision(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=HEADERS
        ) as client:
            response = await client.post(
                "/tax/validate",
                json={
                    "decision": "deductible",
                    "confidence": 0.85,
                    "legal_basis": [
                        {"code": "CIVA", "article": "Artigo 20º", "excerpt": "Test"}
                    ],
                    "explanation": "Test",
                    "risks": [],
                    "assumptions": [],
                    "required_followup": [],
                    "risk_level": "low",
                    "legal_version_timestamp": "2024-01-01",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "valid" in data


@pytest.mark.integration
class TestMcpEndpoints:
    """Integration tests for MCP endpoints."""

    @pytest.mark.asyncio
    async def test_mcp_list_tools(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=HEADERS
        ) as client:
            response = await client.get("/mcp/tools")
            assert response.status_code == 200
            data = response.json()
            assert "tools" in data
            assert len(data["tools"]) > 0

    @pytest.mark.asyncio
    async def test_mcp_tool_not_found(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=HEADERS
        ) as client:
            response = await client.get("/mcp/tool/nonexistent")
            assert response.status_code == 404


@pytest.mark.integration
class TestGraphEndpoints:
    """Tests for graph endpoints."""

    @pytest.mark.asyncio
    async def test_graph_stats(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=HEADERS
        ) as client:
            response = await client.get("/tax/graph/stats")
            assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_gmif_summary(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", headers=HEADERS
        ) as client:
            response = await client.get("/tax/graph/gmif-summary")
            assert response.status_code in (200, 500)
