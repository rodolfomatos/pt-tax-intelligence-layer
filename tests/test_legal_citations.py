"""
Tests for LegalCitationService.

Tests the service that fetches legal citations from ptdata API with fallback.
"""

import pytest
from app.services.legal_citations import LegalCitationService, get_citation_service


class TestLegalCitationService:
    """Test cases for LegalCitationService."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        return LegalCitationService()

    def test_fallback_citations_defined(self, service):
        """Should have fallback citations for common articles."""
        assert ("CIVA", "6") in service.FALLBACK_CITATIONS
        assert ("CIVA", "2") in service.FALLBACK_CITATIONS
        assert ("CIVA", "20") in service.FALLBACK_CITATIONS
        assert ("CIRC", "23") in service.FALLBACK_CITATIONS
        assert ("CIRC", "39") in service.FALLBACK_CITATIONS

    @pytest.mark.asyncio
    async def test_get_citation_from_fallback_when_no_client(self, service, monkeypatch):
        """Should return fallback when client not initialized and API fails."""
        monkeypatch.setattr(service, "_client", None, raising=False)
        service._cache = {}

        import app.data.ptdata.client as ptdata_client_module
        monkeypatch.setattr(ptdata_client_module, "get_ptdata_client", lambda: None)

        result = await service.get_citation("CIVA", "20")
        assert result is not None
        assert result.code == "CIVA"
        # Fallback article includes "Artigo" prefix
        assert "20" in result.article

    @pytest.mark.asyncio
    async def test_get_citation_caches_result(self, service, monkeypatch):
        """Should cache citation after first fetch."""
        class MockClient:
            async def get_article(self, code, article):
                return {"content": "Test article"}

        service._client = MockClient()
        service._cache = {}

        # First call
        result1 = await service.get_citation("CIVA", "20")
        # Second call should hit cache
        result2 = await service.get_citation("CIVA", "20")

        assert result1.code == result2.code
        # Cache key should be set
        assert ("CIVA", "20") in service._cache

    @pytest.mark.asyncio
    async def test_search_citations_returns_list(self, service, monkeypatch):
        """Should return list of LegalCitation."""
        class MockClient:
            async def search_legislation(self, query, code, limit):
                return [
                    {"code": "CIVA", "article": "20º", "excerpt": "..."},
                    {"code": "CIRC", "article": "23º", "excerpt": "..."},
                ]

        service._client = MockClient()
        results = await service.search_citations("test query", code="CIVA")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_current_version_returns_timestamp(self, service, monkeypatch):
        """Should return timestamp string."""
        class MockClient:
            async def get_legal_version_timestamp(self):
                return "2024-01-01T00:00:00Z"

        service._client = MockClient()
        version = await service.get_current_version()
        assert isinstance(version, str)

    def test_singleton_pattern(self):
        """get_citation_service should return same instance."""
        s1 = get_citation_service()
        s2 = get_citation_service()
        assert s1 is s2
