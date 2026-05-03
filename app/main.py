"""
PT Tax Intelligence Layer - Main Application.

Backend decision engine for Portuguese tax law analysis.
Refactored to use routers for better maintainability.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.models import HealthResponse
from app.database.session import init_db, close_db
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.api_auth import APIKeyMiddleware
from app.middleware.metrics import setup_metrics
from app.data.memory.graph.visualization import router as graph_viz_router
from app.routers import tax, decisions, search, graph, dashboard, mcp, internal

settings = get_settings()

# Initialize Sentry if DSN configured
if settings.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=settings.sentry_traces_sample_rate or 0.1,
        environment=settings.environment or "production",
        debug=settings.log_level == "DEBUG",
    )
    logger = logging.getLogger(__name__)
    logger.info("Sentry initialized")

if settings.log_level == "DEBUG":
    logging.basicConfig(
        level=settings.log_level,
        format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}',
    )
else:
    logging.basicConfig(level=settings.log_level)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("PT Tax Intelligence Layer starting...")
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")

    yield

    logger.info("PT Tax Intelligence Layer shutting down...")
    from app.data.ptdata.client import get_ptdata_client
    from app.data.cache.client import get_cache_client
    from app.middleware.rate_limit_backends import get_rate_limit_backend

    ptdata = await get_ptdata_client()
    await ptdata.close()

    cache = await get_cache_client()
    await cache.close()

    rate_limit_backend = await get_rate_limit_backend()
    await rate_limit_backend.close()

    await close_db()


app = FastAPI(
    title="PT Tax Intelligence Layer",
    description="Backend decision engine for Portuguese tax law analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# Add middleware
setup_metrics(app)

app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_per_minute,
    requests_per_hour=settings.rate_limit_per_hour,
    burst_limit=settings.rate_limit_burst,
)

if settings.api_key:
    app.add_middleware(APIKeyMiddleware)

# Include routers
app.include_router(tax.router)
app.include_router(decisions.router)
app.include_router(search.router)
app.include_router(graph.router)
app.include_router(dashboard.router)
app.include_router(mcp.router)
app.include_router(internal.router)
app.include_router(graph_viz_router)


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "detail": exc.errors(),
            "body": str(exc.body)[:200] if exc.body else None,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": request.headers.get("X-Request-ID"),
        },
    )


# Health check - keep in main since it's a core endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint - verifies connectivity to all dependencies."""
    from app.data.ptdata.client import get_ptdata_client
    from app.data.cache.client import get_cache_client

    ptdata = await get_ptdata_client()
    cache = await get_cache_client()

    ptdata_status = "ok" if await ptdata.health_check() else "unavailable"
    cache_status = "ok" if await cache.health_check() else "unavailable"

    db_status = "ok"
    try:
        from app.database.session import get_engine
        from sqlalchemy import text

        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unavailable: {str(e)[:50]}"
        logger.warning(f"Health check DB failed: {e}")

    all_ok = all(s == "ok" for s in [ptdata_status, db_status, cache_status])

    return HealthResponse(
        status="healthy" if all_ok else "degraded",
        version="1.0.0",
        dependencies={
            "ptdata": ptdata_status,
            "database": db_status,
            "cache": cache_status,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
