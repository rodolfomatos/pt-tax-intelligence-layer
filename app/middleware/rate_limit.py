import logging
from typing import Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.middleware.rate_limit_backends import get_rate_limit_backend, RateLimitBackend

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with pluggable backends.

    Default backend: InMemoryBackend (testing)
    Production: RedisBackend via RATE_LIMIT_BACKEND=redis
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = None,
        requests_per_hour: int = None,
        burst_limit: int = None,
        backend: Optional[RateLimitBackend] = None,
    ):
        super().__init__(app)
        # Use provided limits or fall back to settings
        from app.config import get_settings
        settings = get_settings()
        self.requests_per_minute = requests_per_minute or settings.rate_limit_per_minute
        self.requests_per_hour = requests_per_hour or settings.rate_limit_per_hour
        self.burst_limit = burst_limit or settings.rate_limit_burst
        self.backend = backend

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier (API key or IP)."""
        # Check X-API-Key header first (used by APIKeyMiddleware)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api:{api_key[:16]}"
        # Check Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header.replace("Bearer ", "")
            return f"api:{api_key[:16]}"
        return f"ip:{request.client.host if request.client else 'unknown'}"

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        import os

        if os.getenv("TESTING") or request.url.path in [
            "/health",
            "/docs",
            "/openapi.json",
            "/metrics",
        ]:
            return await call_next(request)

        # Get backend (lazy initialization)
        backend = self.backend or await get_rate_limit_backend()

        client_id = self._get_client_id(request)

        try:
            allowed, headers = await backend.check_rate_limit(
                client_id,
                self.requests_per_minute,
                self.requests_per_hour,
                self.burst_limit,
            )
        except Exception as e:
            logger.error(f"Rate limit backend error: {e}")
            # On backend failure, allow request (fail open)
            return await call_next(request)

        for key, value in headers.items():
            request.state.__setattr__(key.lower().replace("-", "_"), value)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_id}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers=headers,
            )

        response = await call_next(request)

        for key, value in headers.items():
            response.headers[key] = value

        return response
