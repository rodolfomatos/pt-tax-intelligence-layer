"""
Tests for MCP router endpoints.

Tests: /mcp/tools, /mcp/execute, /mcp/tool/{tool_name}
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from app.routers.mcp import list_mcp_tools, execute_mcp_tool, get_mcp_tool
from app.models import MCPExecuteInput


@pytest.fixture
def mock_registry(monkeypatch):
    """Mock MCP registry."""
    from app.data.mcp.tools import MCPToolRegistry
    registry = MagicMock(spec=MCPToolRegistry)
    # list_tools returns list of tool objects with to_dict method
    tool1 = MagicMock()
    tool1.to_dict.return_value = {"name": "search_legislation", "description": "Search legislation"}
    tool2 = MagicMock()
    tool2.to_dict.return_value = {"name": "get_article", "description": "Get article"}
    registry.list_tools.return_value = [tool1, tool2]
    registry.get_tool.return_value = tool1
    monkeypatch.setattr("app.routers.mcp.get_mcp_registry", lambda: registry)
    return registry


@pytest.fixture
def mock_executor(monkeypatch):
    """Mock MCP executor."""
    from app.data.mcp.executor import MCPToolExecutor
    executor = AsyncMock(spec=MCPToolExecutor)
    executor.execute = AsyncMock(return_value={"result": "ok"})
    monkeypatch.setattr("app.routers.mcp.get_mcp_executor", lambda: executor)
    return executor


@pytest.mark.asyncio
async def test_list_mcp_tools_dict(mock_registry):
    """Should return list of tools when registry returns dicts."""
    # Simulate registry returning list of dicts
    mock_registry.list_tools.return_value = [{"name": "search", "desc": "..."}]
    result = await list_mcp_tools()
    assert "tools" in result
    assert isinstance(result["tools"], list)


@pytest.mark.asyncio
async def test_list_mcp_tools_objects(mock_registry):
    """Should convert tool objects to dicts."""
    tool = MagicMock()
    tool.to_dict.return_value = {"name": "tool", "desc": "test"}
    mock_registry.list_tools.return_value = [tool]
    result = await list_mcp_tools()
    assert result["tools"][0] == {"name": "tool", "desc": "test"}


@pytest.mark.asyncio
async def test_execute_mcp_tool(mock_executor):
    """Should execute a tool and return result."""
    input_data = MCPExecuteInput(tool_name="search_legislation", parameters={"query": "test"})
    result = await execute_mcp_tool(input_data)
    assert result == {"result": "ok"}
    mock_executor.execute.assert_called_once_with("search_legislation", {"query": "test"})


@pytest.mark.asyncio
async def test_get_mcp_tool_found(mock_registry):
    """Should return tool details."""
    tool = MagicMock()
    tool.to_dict.return_value = {"name": "search", "desc": "search desc"}
    mock_registry.get_tool.return_value = tool
    result = await get_mcp_tool("search")
    assert result == {"name": "search", "desc": "search desc"}


@pytest.mark.asyncio
async def test_get_mcp_tool_not_found(mock_registry):
    """Should raise 404 if tool not found."""
    mock_registry.get_tool.return_value = None
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await get_mcp_tool("unknown")
    assert exc.value.status_code == 404
