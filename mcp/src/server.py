#!/usr/bin/env python3
"""
UP Tax Intelligence MCP Server

Provides tax analysis tools via MCP (Model Context Protocol).
Can run as stdio server or HTTP server.
"""
import sys
import json
import os
from typing import Any, Optional

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    import httpx
except ImportError:
    print("Installing mcp package...", file=sys.stderr)
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp", "httpx"])
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    import httpx

API_URL = os.getenv("UP_TAX_API_URL", "http://localhost:8000")

server = Server("up-tax-intelligence")


def call_api(endpoint: str, data: Optional[dict] = None, method: str = "POST") -> dict:
    """Call the UP Tax Intelligence API."""
    try:
        if method == "POST":
            response = httpx.post(f"{API_URL}{endpoint}", json=data or {}, timeout=30)
        else:
            response = httpx.get(f"{API_URL}{endpoint}", params=data or {}, timeout=30)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        return {"error": str(e), "detail": "API request failed"}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="tax_analyze",
            description="Analyze a Portuguese tax operation for deductibility and legal compliance",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation_type": {
                        "type": "string",
                        "enum": ["expense", "invoice", "asset", "contract"],
                        "description": "Type of operation to analyze"
                    },
                    "description": {"type": "string", "description": "Description of the operation"},
                    "amount": {"type": "number", "description": "Amount in EUR"},
                    "entity_type": {
                        "type": "string",
                        "enum": ["university", "researcher", "department", "project"],
                        "description": "Type of entity"
                    },
                    "context": {
                        "type": "object",
                        "properties": {
                            "project_type": {"enum": ["FCT", "Horizon", "internal", "other"]},
                            "activity_type": {"enum": ["taxable", "exempt", "mixed"]},
                            "location": {"enum": ["PT", "EU", "non-EU"]},
                        },
                        "required": ["project_type", "activity_type", "location"]
                    }
                },
                "required": ["operation_type", "description", "amount", "entity_type", "context"]
            }
        ),
        Tool(
            name="tax_validate",
            description="Validate an existing tax decision for consistency",
            inputSchema={
                "type": "object",
                "properties": {
                    "decision": {"enum": ["deductible", "non_deductible", "partially_deductible", "uncertain"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "legal_basis": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "article": {"type": "string"},
                                "excerpt": {"type": "string"}
                            }
                        }
                    },
                    "explanation": {"type": "string"},
                    "risk_level": {"enum": ["low", "medium", "high"]},
                },
                "required": ["decision", "confidence", "legal_basis", "explanation", "risk_level"]
            }
        ),
        Tool(
            name="tax_search",
            description="Search Portuguese tax legislation",
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Search query"},
                    "code": {"type": "string", "description": "Tax code filter (CIVA, CIRC, etc.)"},
                    "limit": {"type": "number", "default": 10},
                },
                "required": ["q"]
            }
        ),
        Tool(
            name="tax_decisions",
            description="List past tax decisions",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "number", "default": 100},
                    "offset": {"type": "number", "default": 0},
                    "decision_type": {"type": "string"},
                    "entity_type": {"type": "string"},
                }
            }
        ),
        Tool(
            name="dashboard_summary",
            description="Get aggregated dashboard statistics",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="health_check",
            description="Check if the API is running and healthy",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    """Handle tool calls."""
    arguments = arguments or {}
    
    try:
        if name == "tax_analyze":
            result = call_api("/tax/analyze", arguments)
        elif name == "tax_validate":
            result = call_api("/tax/validate", arguments)
        elif name == "tax_search":
            result = call_api("/tax/search", arguments, method="GET")
        elif name == "tax_decisions":
            result = call_api("/tax/decisions", arguments, method="GET")
        elif name == "dashboard_summary":
            result = call_api("/dashboard/summary", method="GET")
        elif name == "health_check":
            result = call_api("/health", method="GET")
        else:
            result = {"error": f"Unknown tool: {name}"}
    except Exception as e:
        result = {"error": str(e)}
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def main():
    """Run the MCP server."""
    import asyncio
    asyncio.run(stdio_server(server))


if __name__ == "__main__":
    main()