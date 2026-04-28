import time
import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter using sliding window.

    For production, consider using Redis-backed rate limiting.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit

        self._minute_cache: dict[str, list[float]] = {}
        self._hour_cache: dict[str, list[float]] = {}

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

    def _cleanup_old_entries(
        self, timestamps: list[float], max_age: float
    ) -> list[float]:
        """Remove old timestamps."""
        cutoff = time.time() - max_age
        return [ts for ts in timestamps if ts > cutoff]

    def _check_rate_limit(self, client_id: str) -> tuple[bool, dict]:
        """Check if request is within rate limits."""
        now = time.time()

        minute_window = 60
        hour_window = 3600

        if client_id not in self._minute_cache:
            self._minute_cache[client_id] = []
        if client_id not in self._hour_cache:
            self._hour_cache[client_id] = []

        self._minute_cache[client_id] = self._cleanup_old_entries(
            self._minute_cache[client_id], minute_window
        )
        self._hour_cache[client_id] = self._cleanup_old_entries(
            self._hour_cache[client_id], hour_window
        )

        minute_count = len(self._minute_cache[client_id])
        hour_count = len(self._hour_cache[client_id])

        remaining_minute = self.requests_per_minute - minute_count
        remaining_hour = self.requests_per_hour - hour_count

        headers = {
            "X-RateLimit-Limit-Per-Minute": str(self.requests_per_minute),
            "X-RateLimit-Limit-Per-Hour": str(self.requests_per_hour),
            "X-RateLimit-Remaining-Per-Minute": str(max(0, remaining_minute)),
            "X-RateLimit-Remaining-Per-Hour": str(max(0, remaining_hour)),
            "X-RateLimit-Reset-Per-Minute": str(int(now + minute_window)),
            "X-RateLimit-Reset-Per-Hour": str(int(now + hour_window)),
        }

        if minute_count >= self.requests_per_minute:
            return False, headers
        if hour_count >= self.requests_per_hour:
            return False, headers
        if minute_count >= self.burst_limit and minute_count < self.requests_per_minute:
            return False, headers

        self._minute_cache[client_id].append(now)
        self._hour_cache[client_id].append(now)

        return True, headers

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

        client_id = self._get_client_id(request)

        allowed, headers = self._check_rate_limit(client_id)

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
