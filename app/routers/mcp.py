"""
MCP tools router.

Contains MCP tool listing, execution, and related endpoints.
"""

from fastapi import APIRouter, Query, HTTPException
from app.models import MCPExecuteInput
from app.data.mcp.tools import get_mcp_registry
from app.data.mcp.executor import get_mcp_executor
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP"])


@router.get("/tools")
async def list_mcp_tools():
    """List all available MCP tools."""
    registry = get_mcp_registry()
    tools = registry.list_tools()
    # Handle both dict and object returns
    if tools and isinstance(tools[0], dict):
        return {"tools": tools}
    return {"tools": [t.to_dict() for t in tools]}


@router.post("/execute")
async def execute_mcp_tool(input: MCPExecuteInput):
    """
    Execute an MCP tool by name.

    Args:
        input: MCPExecuteInput with tool_name and parameters

    Returns:
        Tool execution result or error
    """
    executor = get_mcp_executor()
    result = await executor.execute(input.tool_name, input.parameters)
    return result


@router.get("/tool/{tool_name}")
async def get_mcp_tool(tool_name: str):
    """Get details of a specific MCP tool."""
    registry = get_mcp_registry()
    tool = registry.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    return tool.to_dict()
