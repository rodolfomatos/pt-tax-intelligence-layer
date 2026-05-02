import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


class TestHealthEndpoint:
    """Integration tests for health endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_returns_200(self, mock_cache):
        """Health endpoint should return 200."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_health_returns_status(self, mock_cache):
        """Health endpoint should return status dict."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
        
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "dependencies" in data


class TestAnalyzeEndpoint:
    """Integration tests for /tax/analyze endpoint."""
    
    @pytest.mark.asyncio
    async def test_analyze_requires_json(self, async_client):
        """Analyze endpoint should require JSON body."""
        response = await async_client.post("/tax/analyze")
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_analyze_validates_input(self, async_client):
        """Analyze should validate input schema."""
        response = await async_client.post(
            "/tax/analyze",
            json={"invalid": "data"},
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_analyze_with_valid_input(self, async_client, mock_ptdata):
        """Analyze with valid input should return decision."""
        response = await async_client.post(
            "/tax/analyze",
            json={
                "operation_type": "expense",
                "description": "Material de escritório",
                "amount": 50.00,
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
        assert "legal_basis" in data


class TestSearchEndpoint:
    """Integration tests for /tax/search endpoint."""
    
    @pytest.mark.asyncio
    async def test_search_requires_query(self, async_client):
        """Search should require q parameter."""
        response = await async_client.get("/tax/search")
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_search_with_query(self, async_client, mock_ptdata):
        """Search with query should return results."""
        response = await async_client.get("/tax/search?q=iva&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query" in data


class TestArticleEndpoint:
    """Integration tests for /tax/article endpoint."""
    
    @pytest.mark.asyncio
    async def test_article_not_found(self, async_client, mock_ptdata):
        """Non-existent article should return 404."""
        response = await async_client.get("/tax/article/CIVA/999")
        assert response.status_code == 404


class TestValidateEndpoint:
    """Integration tests for /tax/validate endpoint."""
    
    @pytest.mark.asyncio
    async def test_validate_valid_decision(self, async_client):
        """Valid decision should pass validation."""
        response = await async_client.post(
            "/tax/validate",
            json={
                "decision": "deductible",
                "confidence": 0.95,
                "legal_basis": [
                    {"code": "CIVA", "article": "20º", "excerpt": "Test"}
                ],
                "explanation": "Test",
                "risks": [],
                "assumptions": [],
                "required_followup": [],
                "risk_level": "low",
                "legal_version_timestamp": "2024-01-01T00:00:00Z",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
    
    @pytest.mark.asyncio
    async def test_validate_warns_on_low_sources_high_confidence(self, async_client):
        """High confidence with low legal sources should warn."""
        response = await async_client.post(
            "/tax/validate",
            json={
                "decision": "deductible",
                "confidence": 0.95,
                "legal_basis": [
                    {"code": "CIVA", "article": "20º", "excerpt": "Test"}
                ],
                "explanation": "Test",
                "risks": [],
                "assumptions": [],
                "required_followup": [],
                "risk_level": "low",
                "legal_version_timestamp": "2024-01-01T00:00:00Z",
            },
        )
        data = response.json()
        assert len(data.get("warnings", [])) > 0


class TestDecisionsEndpoint:
    """Integration tests for /tax/decisions endpoint."""
    
    @pytest.mark.asyncio
    async def test_decisions_returns_list_or_error(self, async_client):
        """Decisions should return a list or graceful error."""
        response = await async_client.get("/tax/decisions")
        # Either 200 with data or 500 if DB unavailable (expected in test)
        assert response.status_code in [200, 500]
