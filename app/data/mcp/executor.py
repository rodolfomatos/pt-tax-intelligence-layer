"""
MCP Tool Executor

Executes MCP tool calls by delegating to appropriate services.
"""

from typing import Optional, Dict, Any
import logging
from app.data.ptdata.client import get_ptdata_client
from app.data.cache.client import get_cache_client
from app.database.audit import get_audit_repository

logger = logging.getLogger(__name__)


class MCPToolExecutor:
    """Executor for MCP tools."""
    
    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a tool by name with given parameters."""
        
        executors = {
            "search_legislation": self._search_legislation,
            "search_jurisprudence": self._search_jurisprudence,
            "get_tax_rulings": self._get_tax_rulings,
            "get_official_interpretations": self._get_official_interpretations,
            "get_article": self._get_article,
            "search_decisions": self._search_decisions,
        }
        
        executor = executors.get(tool_name)
        if not executor:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            return await executor(parameters)
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            return {"error": str(e)}
    
    async def _search_legislation(self, params: Dict[str, Any]) -> Dict:
        query = params.get("query", "")
        code = params.get("code")
        article = params.get("article")
        limit = params.get("limit", 10)
        
        ptdata = await get_ptdata_client()
        cache = await get_cache_client()
        
        # Check cache
        cached = await cache.search_legislation(query, code)
        if cached:
            return {"results": cached[:limit], "total": len(cached), "cached": True}
        
        results = await ptdata.search_legislation(query, code, limit)
        
        if results:
            await cache.set_search_legislation(query, code, results)
        
        return {"results": results, "total": len(results), "cached": False}
    
    async def _search_jurisprudence(self, params: Dict[str, Any]) -> Dict:
        query = params.get("query", "")
        court = params.get("court")
        year = params.get("year")
        limit = params.get("limit", 10)
        
        ptdata = await get_ptdata_client()
        
        results = await ptdata.search_jurisprudence(query, court, year, limit)
        
        return {"results": results, "total": len(results)}
    
    async def _get_tax_rulings(self, params: Dict[str, Any]) -> Dict:
        code = params.get("code", "")
        topic = params.get("topic")
        year = params.get("year")
        limit = params.get("limit", 10)
        
        ptdata = await get_ptdata_client()
        
        results = await ptdata.get_tax_rulings(code, topic, year, limit)
        
        return {"results": results, "total": len(results)}
    
    async def _get_official_interpretations(self, params: Dict[str, Any]) -> Dict:
        code = params.get("code", "")
        subject = params.get("subject", "")
        limit = params.get("limit", 10)
        
        ptdata = await get_ptdata_client()
        
        results = await ptdata.get_official_interpretations(code, subject, limit)
        
        return {"results": results, "total": len(results)}
    
    async def _get_article(self, params: Dict[str, Any]) -> Dict:
        code = params.get("code", "")
        article = params.get("article", "")
        
        cache = await get_cache_client()
        ptdata = await get_ptdata_client()
        
        # Check cache
        cached = await cache.get_article(code, article)
        if cached:
            return {"article": cached, "cached": True}
        
        result = await ptdata.get_article(code, article)
        
        if result:
            await cache.set_article(code, article, result)
            return {"article": result, "cached": False}
        
        return {"error": f"Article {code}/{article} not found"}
    
    async def _search_decisions(self, params: Dict[str, Any]) -> Dict:
        query = params.get("query", "")
        decision_type = params.get("decision_type")
        entity_type = params.get("entity_type")
        limit = params.get("limit", 10)
        
        audit = get_audit_repository()
        
        decisions = await audit.get_decisions(
            limit=limit,
            decision_type=decision_type,
            entity_type=entity_type,
        )
        
        # Filter by query if provided
        if query:
            decisions = [d for d in decisions if query.lower() in d.description.lower()]
        
        return {
            "results": [
                {
                    "id": str(d.id),
                    "description": d.description,
                    "decision": d.decision,
                    "confidence": d.confidence,
                    "created_at": d.created_at.isoformat(),
                }
                for d in decisions
            ],
            "total": len(decisions),
        }


# Singleton
_executor: Optional[MCPToolExecutor] = None


def get_mcp_executor() -> MCPToolExecutor:
    global _executor
    if _executor is None:
        _executor = MCPToolExecutor()
    return _executor