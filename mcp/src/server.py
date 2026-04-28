#!/usr/bin/env python3
"""
PT Tax Intelligence MCP Server

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

API_URL = os.getenv("PT_TAX_API_URL", "http://localhost:8000")


def call_api(endpoint: str, data: Optional[dict] = None, method: str = "POST") -> dict:
    """Call the PT Tax Intelligence API."""
    try:
        if method == "POST":
            response = httpx.post(f"{API_URL}{endpoint}", json=data or {}, timeout=30)
        else:
            response = httpx.get(f"{API_URL}{endpoint}", params=data or {}, timeout=30)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        return {"error": str(e), "detail": "API request failed"}


server = Server("pt-tax-intelligence")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="tax_analyze",
            description="Analyze a tax operation and get a structured decision based on Portuguese tax law.",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation_type": {
                        "type": "string",
                        "enum": ["expense", "invoice", "asset", "contract"],
                        "description": "Type of operation",
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the operation",
                    },
                    "amount": {"type": "number", "description": "Amount in EUR"},
                    "currency": {"type": "string", "default": "EUR"},
                    "entity_type": {
                        "type": "string",
                        "enum": ["university", "researcher", "department", "project"],
                    },
                    "context": {
                        "type": "object",
                        "properties": {
                            "project_type": {
                                "type": "string",
                                "enum": ["FCT", "Horizon", "internal", "other"],
                            },
                            "activity_type": {
                                "type": "string",
                                "enum": ["taxable", "exempt", "mixed"],
                            },
                            "location": {
                                "type": "string",
                                "enum": ["PT", "EU", "non-EU"],
                            },
                        },
                    },
                },
                "required": [
                    "operation_type",
                    "description",
                    "amount",
                    "currency",
                    "entity_type",
                ],
            },
        ),
        Tool(
            name="tax_validate",
            description="Validate an existing tax decision against Portuguese tax law.",
            inputSchema={
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "string",
                        "enum": [
                            "deductible",
                            "non_deductible",
                            "partially_deductible",
                            "uncertain",
                        ],
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "legal_basis": {"type": "array", "items": {"type": "object"}},
                    "explanation": {"type": "string"},
                    "risks": {"type": "array", "items": {"type": "string"}},
                    "assumptions": {"type": "array", "items": {"type": "string"}},
                    "required_followup": {"type": "array", "items": {"type": "string"}},
                    "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                    "legal_version_timestamp": {"type": "string"},
                },
                "required": ["decision", "confidence", "legal_basis", "explanation"],
            },
        ),
        Tool(
            name="tax_search",
            description="Search Portuguese tax legislation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "code": {
                        "type": "string",
                        "description": "Law code (e.g., CIVA, CIRC)",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="tax_decisions",
            description="List past tax decisions with optional filters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "string",
                        "enum": [
                            "deductible",
                            "non_deductible",
                            "partially_deductible",
                            "uncertain",
                        ],
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "offset": {"type": "integer", "default": 0, "minimum": 0},
                },
            },
        ),
        Tool(
            name="tax_article",
            description="Retrieve a specific tax law article.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Law code (e.g., CIVA)"},
                    "article": {
                        "type": "string",
                        "description": "Article number (e.g., 20)",
                    },
                },
                "required": ["code", "article"],
            },
        ),
        Tool(
            name="dashboard_summary",
            description="Get a summary of tax decision statistics for dashboard display.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool execution."""
    try:
        if name == "tax_analyze":
            result = call_api("/tax/analyze", arguments)
        elif name == "tax_validate":
            result = call_api("/tax/validate", arguments)
        elif name == "tax_search":
            query = arguments.get("query", "")
            code = arguments.get("code")
            params = {"q": query}
            if code:
                params["code"] = code
            result = call_api("/tax/search", params, method="GET")
        elif name == "tax_decisions":
            params = {}
            if "decision" in arguments:
                params["decision"] = arguments["decision"]
            if "limit" in arguments:
                params["limit"] = arguments["limit"]
            if "offset" in arguments:
                params["offset"] = arguments["offset"]
            result = call_api("/tax/decisions", params, method="GET")
        elif name == "tax_article":
            code = arguments.get("code", "")
            article = arguments.get("article", "")
            result = call_api(f"/tax/article/{code}/{article}", method="GET")
        elif name == "dashboard_summary":
            result = call_api("/dashboard/summary", method="GET")
        else:
            result = {"error": f"Unknown tool: {name}"}

        # Check for errors
        if "error" in result:
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        return [
            TextContent(
                type="text", text=json.dumps(result, indent=2, ensure_ascii=False)
            )
        ]
    except Exception as e:
        error_result = {"error": str(e), "tool": name, "arguments": arguments}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
