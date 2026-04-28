"""
Prometheus metrics for monitoring.

Exposes request counts, latencies, and error rates.
"""

import time
import logging
from fastapi import FastAPI, Request
from starlette.responses import Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_latency_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

ERROR_COUNT = Counter(
    "http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "error_type"]
)

DECISION_COUNT = Counter(
    "tax_decisions_total",
    "Total tax decisions",
    ["decision", "entity_type", "project_type"]
)

CONFIDENCE_SUM = Counter(
    "tax_confidence_sum",
    "Sum of confidence scores"
)


def setup_metrics(app: FastAPI):
    """Setup metrics middleware and endpoint."""
    
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        latency = time.time() - start_time
        method = request.method
        endpoint = get_endpoint_name(request)
        status = response.status_code
        
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
        
        if status >= 400:
            ERROR_COUNT.labels(
                method=method,
                endpoint=endpoint,
                error_type=str(status)
            ).inc()
        
        return response
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )


def get_endpoint_name(request: Request) -> str:
    """Extract endpoint name from path."""
    path = request.url.path
    
    if path.startswith("/tax/"):
        return "/tax/*"
    if path.startswith("/mcp/"):
        return "/mcp/*"
    if path.startswith("/graph/"):
        return "/graph/*"
    
    return path


def record_decision(decision: str, entity_type: str, project_type: str, confidence: float):
    """Record a tax decision for metrics."""
    DECISION_COUNT.labels(
        decision=decision,
        entity_type=entity_type,
        project_type=project_type
    ).inc()
    CONFIDENCE_SUM.inc(confidence)