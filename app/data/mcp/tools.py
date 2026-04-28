"""
MCP (Model Context Protocol) Tools for external queries.

Provides standardized tools for querying external data sources:
- Legislation search (ptdata)
- Jurisprudence search
- Tax rulings
- Official interpretations
"""

from typing import Optional, List, Dict, Any
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ToolType(str, Enum):
    LEGISLATION_SEARCH = "legislation_search"
    JURISPRUDENCE_SEARCH = "jurisprudence_search"
    TAX_RULINGS = "tax_rulings"
    OFFICIAL_INTERPRETATIONS = "official_interpretations"
    ARTICLE_LOOKUP = "article_lookup"
    DECISION_SEARCH = "decision_search"


class MCPTool:
    """Base class for MCP tools."""
    
    def __init__(self, tool_type: ToolType, description: str, parameters: Dict[str, Any]):
        self.tool_type = tool_type
        self.description = description
        self.parameters = parameters
    
    def to_dict(self) -> Dict:
        return {
            "type": self.tool_type.value,
            "description": self.description,
            "parameters": self.parameters,
        }


class MCPToolRegistry:
    """Registry of available MCP tools."""
    
    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        self._tools["search_legislation"] = MCPTool(
            tool_type=ToolType.LEGISLATION_SEARCH,
            description="Search Portuguese tax legislation by keyword, code, or article",
            parameters={
                "query": {"type": "string", "description": "Search keywords"},
                "code": {"type": "string", "description": "Tax code filter (CIVA, CIRC, CRP, etc.)", "optional": True},
                "article": {"type": "string", "description": "Specific article number", "optional": True},
                "limit": {"type": "integer", "description": "Max results", "default": 10},
            }
        )
        
        self._tools["search_jurisprudence"] = MCPTool(
            tool_type=ToolType.JURISPRUDENCE_SEARCH,
            description="Search tax jurisprudence and court decisions",
            parameters={
                "query": {"type": "string", "description": "Search keywords"},
                "court": {"type": "string", "description": "Court type (TC, TCA, STJ)", "optional": True},
                "year": {"type": "integer", "description": "Judgment year", "optional": True},
                "limit": {"type": "integer", "description": "Max results", "default": 10},
            }
        )
        
        self._tools["get_tax_rulings"] = MCPTool(
            tool_type=ToolType.TAX_RULINGS,
            description="Get official tax rulings (acórdãos) from tax courts",
            parameters={
                "code": {"type": "string", "description": "Tax code (CIVA, IRC, etc.)"},
                "topic": {"type": "string", "description": "Topic keyword", "optional": True},
                "year": {"type": "integer", "description": "Year filter", "optional": True},
                "limit": {"type": "integer", "description": "Max results", "default": 10},
            }
        )
        
        self._tools["get_official_interpretations"] = MCPTool(
            tool_type=ToolType.OFFICIAL_INTERPRETATIONS,
            description="Get official interpretations from tax authorities (DGITA, AT)",
            parameters={
                "code": {"type": "string", "description": "Tax code"},
                "subject": {"type": "string", "description": "Subject keyword"},
                "limit": {"type": "integer", "description": "Max results", "default": 10},
            }
        )
        
        self._tools["get_article"] = MCPTool(
            tool_type=ToolType.ARTICLE_LOOKUP,
            description="Get specific article from tax code",
            parameters={
                "code": {"type": "string", "description": "Tax code (CIVA, CIRC, CRP, etc.)"},
                "article": {"type": "string", "description": "Article number (e.g., '17', '23.1')"},
            }
        )
        
        self._tools["search_decisions"] = MCPTool(
            tool_type=ToolType.DECISION_SEARCH,
            description="Search past UP tax decisions for similar cases",
            parameters={
                "query": {"type": "string", "description": "Description or keywords"},
                "decision_type": {"type": "string", "description": "Filter by decision type", "optional": True},
                "entity_type": {"type": "string", "description": "Filter by entity type", "optional": True},
                "limit": {"type": "integer", "description": "Max results", "default": 10},
            }
        )
    
    def list_tools(self) -> List[Dict]:
        """List all available tools."""
        return [tool.to_dict() for tool in self._tools.values()]
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a specific tool by name."""
        return self._tools.get(name)
    
    def get_tool_names(self) -> List[str]:
        """Get list of tool names."""
        return list(self._tools.keys())


# Singleton instance
_registry: Optional[MCPToolRegistry] = None


def get_mcp_registry() -> MCPToolRegistry:
    global _registry
    if _registry is None:
        _registry = MCPToolRegistry()
    return _registry