import logging
from typing import Optional
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PTDataClient:
    """Client for ptdata MCP API - Portuguese tax legislation."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.ptdata_api_key
        self.base_url = base_url or settings.ptdata_api_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
    
    async def close(self):
        await self.client.aclose()
    
    async def search_legislation(
        self,
        query: str,
        code: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search legislation by query."""
        try:
            response = await self.client.post(
                "/mcp",
                json={
                    "action": "search",
                    "query": query,
                    "code": code,
                    "limit": limit,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except httpx.HTTPError as e:
            logger.warning(f"ptdata search failed: {e}")
            return []
    
    async def get_article(self, code: str, article: str) -> Optional[dict]:
        """Get specific article from tax code."""
        try:
            response = await self.client.post(
                "/mcp",
                json={
                    "action": "get_article",
                    "code": code,
                    "article": article,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("article")
        except httpx.HTTPError as e:
            logger.warning(f"ptdata get_article failed: {e}")
            return None
    
    async def get_legal_version_timestamp(self) -> str:
        """Get current legal version timestamp."""
        try:
            response = await self.client.post(
                "/mcp",
                json={"action": "version"},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("timestamp", "2024-01-01T00:00:00Z")
        except httpx.HTTPError:
            return "2024-01-01T00:00:00Z"
    
    async def health_check(self) -> bool:
        """Check if ptdata API is available."""
        try:
            response = await self.client.post("/mcp", json={"action": "ping"})
            return response.status_code == 200
        except httpx.HTTPError:
            return False
    
    async def search_jurisprudence(
        self,
        query: str,
        court: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search tax jurisprudence and court decisions."""
        try:
            response = await self.client.post(
                "/mcp",
                json={
                    "action": "search_jurisprudence",
                    "query": query,
                    "court": court,
                    "year": year,
                    "limit": limit,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except httpx.HTTPError as e:
            logger.warning(f"ptdata search_jurisprudence failed: {e}")
            return []
    
    async def get_tax_rulings(
        self,
        code: str,
        topic: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Get official tax rulings (acórdãos) from tax courts."""
        try:
            response = await self.client.post(
                "/mcp",
                json={
                    "action": "get_tax_rulings",
                    "code": code,
                    "topic": topic,
                    "year": year,
                    "limit": limit,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except httpx.HTTPError as e:
            logger.warning(f"ptdata get_tax_rulings failed: {e}")
            return []
    
    async def get_official_interpretations(
        self,
        code: str,
        subject: str,
        limit: int = 10,
    ) -> list[dict]:
        """Get official interpretations from tax authorities (DGITA, AT)."""
        try:
            response = await self.client.post(
                "/mcp",
                json={
                    "action": "get_interpretations",
                    "code": code,
                    "subject": subject,
                    "limit": limit,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except httpx.HTTPError as e:
            logger.warning(f"ptdata get_official_interpretations failed: {e}")
            return []


_client: Optional[PTDataClient] = None


async def get_ptdata_client() -> PTDataClient:
    global _client
    if _client is None:
        _client = PTDataClient()
    return _client
