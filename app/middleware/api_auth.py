"""
API Key Authentication Middleware.

Protects sensitive endpoints with API key authentication.
"""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PUBLIC_PATHS = {"/health", "/mcp/tools", "/mcp/tool", "/docs", "/openapi.json", "/redoc"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication.
    
    Validates X-API-Key header on protected endpoints.
    Public endpoints are exempt from authentication.
    """
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        if path in PUBLIC_PATHS or path.startswith("/mcp/tool/"):
            return await call_next(request)
        
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            logger.warning(f"Missing API key for {path}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing X-API-Key header"},
            )
        
        if api_key != settings.api_key:
            logger.warning(f"Invalid API key for {path}")
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid API key"},
            )
        
        return await call_next(request)