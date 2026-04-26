"""
Legal Citation Service.

Fetches legal citations from ptdata API instead of using hardcoded values.
"""

import logging
from typing import Optional
from app.data.ptdata.client import get_ptdata_client
from app.models import LegalCitation

logger = logging.getLogger(__name__)


class LegalCitationService:
    """
    Service for fetching legal citations from ptdata API.
    
    Provides fallback to hardcoded values if API is unavailable.
    """
    
    FALLBACK_CITATIONS = {
        ("CIVA", "6"): LegalCitation(
            code="CIVA",
            article="Artigo 6º",
            excerpt="Estão isentas as operações..."
        ),
        ("CIVA", "2"): LegalCitation(
            code="CIVA",
            article="Artigo 2º",
            excerpt="O imposto incide sobre as transmissões de bens..."
        ),
        ("CIVA", "20"): LegalCitation(
            code="CIVA",
            article="Artigo 20º",
            excerpt="São dedutíveis as despesas..."
        ),
        ("CIRC", "23"): LegalCitation(
            code="CIRC",
            article="Artigo 23º",
            excerpt="Os custos são dedutíveis..."
        ),
        ("CIRC", "39"): LegalCitation(
            code="CIRC",
            article="Artigo 39º",
            excerpt="Os ativos fixos tangíveis são amortizáveis..."
        ),
    }
    
    def __init__(self):
        self._client = None
        self._cache: dict = {}
    
    async def get_citation(self, code: str, article: str) -> Optional[LegalCitation]:
        """Get a legal citation for a specific code and article."""
        key = (code.upper(), article)
        
        if key in self._cache:
            return self._cache[key]
        
        article_clean = article.replace("º", "").replace(".", "")
        
        if self._client is None:
            self._client = await get_ptdata_client()
        
        try:
            result = await self._client.get_article(code.upper(), article_clean)
            if result:
                citation = LegalCitation(
                    code=code.upper(),
                    article=article,
                    excerpt=result.get("content", result.get("text", ""))[:200]
                )
                self._cache[key] = citation
                return citation
        except Exception as e:
            logger.warning(f"Failed to fetch {code}/{article}: {e}")
        
        if key in self.FALLBACK_CITATIONS:
            return self.FALLBACK_CITATIONS[key]
        
        return None
    
    async def search_citations(
        self,
        query: str,
        code: Optional[str] = None,
    ) -> list[LegalCitation]:
        """Search for legal citations matching a query."""
        if self._client is None:
            self._client = await get_ptdata_client()
        
        results = await self._client.search_legislation(query, code, limit=5)
        
        citations = []
        for r in results:
            citations.append(LegalCitation(
                code=r.get("code", code or ""),
                article=r.get("article", ""),
                excerpt=r.get("excerpt", r.get("content", ""))[:200]
            ))
        
        return citations
    
    async def get_current_version(self) -> str:
        """Get current legal version timestamp."""
        if self._client is None:
            self._client = await get_ptdata_client()
        
        return await self._client.get_legal_version_timestamp()


_citation_service: Optional[LegalCitationService] = None


def get_citation_service() -> LegalCitationService:
    global _citation_service
    if _citation_service is None:
        _citation_service = LegalCitationService()
    return _citation_service