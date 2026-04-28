import json
import logging
from typing import Optional
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

BASE_URL = "https://api.ptdata.org"
MCP_URL = f"{BASE_URL}/mcp"


class PTDataClient:
    """Client for ptdata API - Portuguese tax data and legislation."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.ptdata_api_key
        self.base_url = base_url or BASE_URL
        self.mcp_url = f"{self.base_url}/mcp"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
        )

    async def close(self):
        await self.client.aclose()

    async def _mcp_call(self, method: str, arguments: dict, id: int = 1) -> dict:
        """Make a JSON-RPC 2.0 call to the MCP endpoint."""
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": method, "arguments": arguments},
            "id": id,
        }
        try:
            response = await self.client.post(self.mcp_url, json=payload)
            response.raise_for_status()
            result = response.json()
            if "error" in result:
                logger.warning(f"MCP error: {result['error']}")
                return {}
            # MCP returns content as list of dicts with 'text' key
            content = result.get("result", {}).get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text", "")
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"text": text}
            return result.get("result", {})
        except httpx.HTTPError as e:
            logger.warning(f"ptdata MCP call failed: {e}")
            return {}

    async def search_legislation(
        self,
        query: str,
        code: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search Portuguese fiscal legislation by keyword."""
        args = {"q": query, "limit": limit}
        if code:
            args["code"] = code
        result = await self._mcp_call("search_legislation", args)
        return result.get("data", result) if isinstance(result, dict) else result

    async def get_article(self, code: str, article: str) -> Optional[dict]:
        """Get full text of a specific article from a Portuguese fiscal law."""
        result = await self._mcp_call(
            "get_law_article",
            {"code": code.lower(), "article": article},
        )
        return result.get("data", result) if isinstance(result, dict) else result

    async def get_legal_version_timestamp(self) -> str:
        """Get current legal version timestamp."""
        result = await self._mcp_call("get_api_status", {})
        return result.get("meta", {}).get("timestamp", "2024-01-01T00:00:00Z")

    async def validate_nif(self, nif: str) -> dict:
        """Validate a Portuguese tax identification number (NIF/NIPC)."""
        result = await self._mcp_call("validate_nif", {"nif": nif})
        return result.get("data", result) if isinstance(result, dict) else result

    async def get_vat_rates(self) -> list[dict]:
        """Get current Portuguese IVA (VAT) rates for all regions."""
        result = await self._mcp_call("get_vat_rates", {})
        return result.get("data", result) if isinstance(result, dict) else result

    async def ask_tax_advice(self, question: str, context: dict = None) -> dict:
        """Ask a tax question to an accountant."""
        args = {"question": question}
        if context:
            args["context"] = context
        result = await self._mcp_call("ask_tax_advice", args)
        return result.get("data", result) if isinstance(result, dict) else result

    async def health_check(self) -> bool:
        """Check if ptdata API is available."""
        try:
            response = await self.client.post(
                self.mcp_url,
                json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1},
            )
            return response.status_code == 200
        except httpx.HTTPError:
            return False


_client: Optional[PTDataClient] = None


async def get_ptdata_client() -> PTDataClient:
    global _client
    if _client is None:
        _client = PTDataClient()
    return _client
