from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import time
from typing import Optional
from datetime import datetime, timedelta
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.models import (
    TaxAnalysisInput, TaxAnalysisOutput,
    TaxValidationInput, TaxValidationOutput,
    HealthResponse,
    Context,
    MCPExecuteInput,
)
from app.services.rules.engine import get_rule_engine
from app.services.reasoning import get_llm_reasoning
from app.services.decision import get_decision_aggregator
from app.data.ptdata.client import get_ptdata_client
from app.data.cache.client import get_cache_client
from app.database.audit import get_audit_repository
from app.database.session import init_db, close_db
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.api_auth import APIKeyMiddleware
from app.data.memory.graph.visualization import router as graph_viz_router

settings = get_settings()

if settings.log_level == "DEBUG":
    logging.basicConfig(
        level=settings.log_level,
        format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'
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
    
    # Cleanup
    ptdata = await get_ptdata_client()
    await ptdata.close()
    
    cache = await get_cache_client()
    await cache.close()
    
    await close_db()


app = FastAPI(
    title="PT Tax Intelligence Layer",
    description="Backend decision engine for Portuguese tax law analysis",
    version="1.0.0",
    lifespan=lifespan,
)

from app.middleware.metrics import setup_metrics
setup_metrics(app)

app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_per_minute,
    requests_per_hour=settings.rate_limit_per_hour,
    burst_limit=settings.rate_limit_burst,
)

if settings.api_key:
    app.add_middleware(APIKeyMiddleware)

app.include_router(graph_viz_router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with consistent JSON format."""
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
    """Handle validation errors with consistent JSON format."""
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
    """Handle unexpected errors with consistent JSON format."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": request.headers.get("X-Request-ID"),
        },
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Verifies connectivity to:
    - ptdata API
    - PostgreSQL database
    - Redis cache
    
    Returns overall system status and dependency states.
    """
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


@app.post("/tax/analyze", response_model=TaxAnalysisOutput)
async def analyze_tax(input: TaxAnalysisInput, request: Request):
    """
    Main tax analysis endpoint.
    
    Processes a tax analysis request through the decision pipeline:
    1. Rule engine (deterministic) - tries to match against known rules
    2. LLM reasoning - if no clear rule match, uses AI for analysis
    3. Decision aggregator - combines results and produces final decision
    
    All decisions are logged for auditability and stored in semantic memory.
    
    Args:
        input: TaxAnalysisInput with operation details
        request: FastAPI request for headers (X-Request-ID, X-User)
    
    Returns:
        TaxAnalysisOutput with decision, confidence, legal basis, and risks
    """
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    logger.info(f"Analyzing: {input.operation_type} - {input.description}")
    
    rule_engine = get_rule_engine()
    llm_reasoning = get_llm_reasoning()
    aggregator = get_decision_aggregator()
    
    # Step 1: Try rule engine (deterministic)
    rule_result = rule_engine.evaluate(input)
    source = "rule_engine" if rule_result else "llm"
    
    # Step 2: Try LLM reasoning (if no clear rule)
    llm_result = await llm_reasoning.analyze(input)
    
    # Step 3: Aggregate and decide
    final_result = await aggregator.decide(input, rule_result, llm_result)
    
    processing_time_ms = int((time.time() - start_time) * 1000)
    
    # Log to audit database
    try:
        audit = get_audit_repository()
        await audit.log_decision(
            input_data=input,
            output_data=final_result,
            source=source,
            processing_time_ms=processing_time_ms,
        )
    except Exception as e:
        logger.error(f"Failed to log decision: {e}")
    
    # Log action
    try:
        audit = get_audit_repository()
        await audit.log_action(
            action="tax_analyze",
            entity_type=input.entity_type,
            user=request.headers.get("X-User", "anonymous"),
            request_id=request_id,
            details={
                "operation_type": input.operation_type,
                "decision": final_result.decision,
                "confidence": final_result.confidence,
            },
            ip_address=request.client.host if request.client else None,
        )
    except Exception as e:
        logger.error(f"Failed to log action: {e}")
    
    # Save to semantic memory (L3 layer)
    try:
        from app.data.memory.layers import get_memory_layers
        from app.data.memory.hooks import DecisionHooks
        
        memory = get_memory_layers()
        memory.save_to_memory(
            decision_id=str(id(final_result)),
            description=input.description,
            decision=final_result.decision,
            explanation=final_result.explanation,
            legal_basis=[lb.model_dump() for lb in final_result.legal_basis],
            metadata={
                "operation_type": input.operation_type,
                "entity_type": input.entity_type,
                "project_type": input.context.project_type,
                "source": source,
            }
        )
        
        DecisionHooks.on_decision(
            decision_id=str(id(final_result)),
            input_data=input.model_dump(),
            output_data=final_result.model_dump(),
        )
    except Exception as e:
        logger.error(f"Failed to save to memory: {e}")
    
    # Save to knowledge graph (GMIF classification)
    try:
        from app.data.memory.graph.builder import get_graph_builder
        from app.data.memory.graph.gmif import get_gmif_classifier
        
        builder = get_graph_builder()
        gmif_type = await builder.add_decision(
            decision_id=str(id(final_result)),
            description=input.description,
            decision_type=final_result.decision,
            confidence=final_result.confidence,
            legal_basis=[lb.model_dump() for lb in final_result.legal_basis],
            entity_type=input.entity_type,
            project_type=input.context.project_type,
            risks=final_result.risks,
            assumptions=final_result.assumptions,
        )
        logger.info(f"GMIF classification: {gmif_type}")
    except Exception as e:
        logger.warning(f"Failed to save to knowledge graph: {e}")
    
    logger.info(f"Decision: {final_result.decision} (confidence: {final_result.confidence})")
    return final_result


@app.post("/tax/validate", response_model=TaxValidationOutput)
async def validate_tax(input: TaxValidationInput, request: Request):
    """
    Validate an existing decision for consistency.
    
    Performs consistency checks on a decision:
    - High confidence but limited legal basis → warning
    - Uncertain decision with high confidence → warning
    - High risk with low confidence → note
    - Missing legal citation fields → warning
    
    Args:
        input: TaxValidationInput with decision to validate
    
    Returns:
        TaxValidationOutput with validation results
    """
    notes = []
    warnings = []
    
    if input.confidence > 0.8 and len(input.legal_basis) < 2:
        warnings.append("High confidence but limited legal basis")
    
    if input.decision == "uncertain" and input.confidence > 0.7:
        warnings.append("Uncertain decision should have lower confidence")
    
    if input.risk_level == "high" and input.confidence < 0.5:
        notes.append("High risk with low confidence - review recommended")
    
    for citation in input.legal_basis:
        if not citation.code or not citation.article:
            warnings.append("Legal citation missing code or article")
    
    return TaxValidationOutput(
        valid=len(warnings) == 0,
        consistency_check="passed" if len(warnings) == 0 else "warnings",
        notes=notes,
        warnings=warnings,
    )


@app.get("/tax/decisions")
async def get_decisions(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    decision_type: Optional[str] = Query(None, description="Filter by decision type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
):
    """
    Get past decisions with pagination and optional filters.
    
    Retrieves historical tax decisions with support for:
    - Pagination via limit/offset
    - Filtering by decision type (deductible, non_deductible, etc.)
    - Filtering by entity type (university, researcher, etc.)
    
    Args:
        limit: Maximum number of results (1-500)
        offset: Number of results to skip
        decision_type: Filter by decision type
        entity_type: Filter by entity type
    
    Returns:
        Dict with decisions list, limit, offset, and total count
    """
    
    try:
        audit = get_audit_repository()
        decisions = await audit.get_decisions(
            limit=limit,
            offset=offset,
            decision_type=decision_type,
            entity_type=entity_type,
        )
        total = await audit.get_decisions_count(
            decision_type=decision_type,
            entity_type=entity_type,
        )
        
        return {
            "decisions": [
                {
                    "id": str(d.id),
                    "created_at": d.created_at.isoformat(),
                    "operation_type": d.operation_type,
                    "description": d.description,
                    "amount": d.amount,
                    "decision": d.decision,
                    "confidence": d.confidence,
                    "risk_level": d.risk_level,
                    "source": d.source,
                }
                for d in decisions
            ],
            "limit": limit,
            "offset": offset,
            "total": total,
        }
    except Exception as e:
        logger.error(f"Failed to get decisions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve decisions")


@app.get("/tax/statistics")
async def get_statistics():
    """Get decision statistics."""
    
    try:
        audit = get_audit_repository()
        stats = await audit.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@app.get("/tax/search")
async def search_legislation(
    q: str = Query(..., description="Search query"),
    code: Optional[str] = Query(None, description="Tax code filter (CIVA, CIRC, etc.)"),
    limit: int = Query(10, ge=1, le=50),
):
    cache = await get_cache_client()
    ptdata = await get_ptdata_client()
    
    cached = await cache.search_legislation(q, code)
    if cached:
        logger.info(f"Cache hit for search: {q}")
        return {"results": cached, "total": len(cached), "query": q, "cached": True}
    
    results = await ptdata.search_legislation(q, code, limit)
    
    if results:
        await cache.set_search_legislation(q, code, results)
    
    return {"results": results, "total": len(results), "query": q, "cached": False}


@app.get("/tax/article/{code}/{article}")
async def get_article(code: str, article: str):
    cache = await get_cache_client()
    ptdata = await get_ptdata_client()
    
    cached = await cache.get_article(code, article)
    if cached:
        return cached
    
    result = await ptdata.get_article(code, article)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Article {code}/{article} not found")
    
    result["last_updated"] = datetime.utcnow().isoformat() + "Z"
    result["version"] = "2024-01-01"
    
    await cache.set_article(code, article, result)
    
    return result


@app.get("/tax/graph/stats")
async def get_graph_stats():
    """Get knowledge graph statistics."""
    try:
        from app.data.memory.graph.query import get_graph_query
        query = get_graph_query()
        stats = await query.get_graph_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get graph stats: {e}")
        raise HTTPException(status_code=500, detail="Graph unavailable")


@app.get("/tax/graph/gmif-summary")
async def get_gmif_summary():
    """Get GMIF classification summary."""
    try:
        from app.data.memory.graph.query import get_graph_query
        query = get_graph_query()
        summary = await query.get_gmif_summary()
        return summary
    except Exception as e:
        logger.error(f"Failed to get GMIF summary: {e}")
        raise HTTPException(status_code=500, detail="Graph unavailable")


@app.get("/tax/graph/decisions-by-gmif/{gmif_type}")
async def get_decisions_by_gmif(gmif_type: str, limit: int = 100):
    """Get all decisions with a specific GMIF type."""
    try:
        from app.data.memory.graph.query import get_graph_query
        query = get_graph_query()
        decisions = await query.get_decisions_by_gmif(gmif_type, limit)
        return {"decisions": decisions, "gmif_type": gmif_type}
    except Exception as e:
        logger.error(f"Failed to get decisions by GMIF: {e}")
        raise HTTPException(status_code=500, detail="Graph unavailable")


@app.get("/tax/graph/contradictions")
async def get_contradictions(decision_id: Optional[str] = None):
    """Get detected contradictions."""
    try:
        from app.data.memory.graph.query import get_graph_query
        query = get_graph_query()
        contradictions = await query.find_contradictions(decision_id)
        return {"contradictions": contradictions}
    except Exception as e:
        logger.error(f"Failed to get contradictions: {e}")
        raise HTTPException(status_code=500, detail="Graph unavailable")


@app.get("/tax/graph/timeline/{entity_external_id}")
async def get_timeline(entity_external_id: str):
    """Get chronological timeline of an entity's decisions."""
    try:
        from app.data.memory.graph.query import get_graph_query
        query = get_graph_query()
        timeline = await query.timeline(entity_external_id)
        return {"timeline": timeline, "entity": entity_external_id}
    except Exception as e:
        logger.error(f"Failed to get timeline: {e}")
        raise HTTPException(status_code=500, detail="Graph unavailable")


# Dashboard Integration Endpoints

@app.get("/dashboard/summary")
async def get_dashboard_summary():
    """
    Dashboard summary - aggregated statistics for UI.
    
    Returns key metrics for dashboard display:
    - Total decisions
    - Decision breakdown
    - Average confidence
    - Recent activity
    """
    try:
        from app.database.audit import get_audit_repository
        from app.data.memory.semantic import get_semantic_memory
        
        audit = get_audit_repository()
        stats = await audit.get_statistics()
        
        semantic = get_semantic_memory()
        memory_count = semantic.count() if semantic else 0
        
        return {
            "total_decisions": stats.get("total", 0),
            "by_decision": stats.get("by_decision", {}),
            "avg_confidence": stats.get("avg_confidence", 0),
            "semantic_memories": memory_count,
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {e}")
        raise HTTPException(status_code=500, detail="Dashboard unavailable")


@app.get("/dashboard/trends")
async def get_dashboard_trends(
    days: int = Query(30, ge=1, le=365),
):
    """
    Dashboard trends - decisions over time.
    
    Args:
        days: Number of days to analyze (default 30)
    """
    try:
        from app.database.audit import get_audit_repository
        
        audit = get_audit_repository()
        start_date = datetime.utcnow() - timedelta(days=days)
        
        decisions = await audit.get_decisions(limit=1000, start_date=start_date)
        
        daily_counts = {}
        for d in decisions:
            date_key = d.created_at.date().isoformat()
            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        
        return {
            "period_days": days,
            "decisions": daily_counts,
            "total": len(decisions),
        }
    except Exception as e:
        logger.error(f"Failed to get trends: {e}")
        raise HTTPException(status_code=500, detail="Trends unavailable")


@app.get("/internal/benchmark")
async def run_benchmark(
    iterations: int = Query(10, ge=1, le=100),
):
    """
    Run performance benchmark.
    
    Tests response times for key operations.
    """
    import time
    
    results = {}
    ptdata = await get_ptdata_client()
    cache = await get_cache_client()
    
    times_health = []
    for _ in range(iterations):
        start = time.time()
        await ptdata.health_check()
        times_health.append(time.time() - start)
    
    results["health_check"] = {
        "avg_ms": sum(times_health) / len(times_health) * 1000,
        "min_ms": min(times_health) * 1000,
        "max_ms": max(times_health) * 1000,
    }
    
    return {"benchmark": results, "iterations": iterations}


# MCP Tools Endpoints

@app.get("/mcp/tools")
async def list_mcp_tools():
    """List all available MCP tools."""
    from app.data.mcp.tools import get_mcp_registry
    registry = get_mcp_registry()
    return {"tools": registry.list_tools()}


@app.post("/mcp/execute", response_model=dict)
async def execute_mcp_tool(input: MCPExecuteInput):
    """
    Execute an MCP tool with given parameters.
    
    Validates input using Pydantic model and executes the tool.
    
    Args:
        input: MCPExecuteInput with tool_name and parameters
    
    Returns:
        Tool execution result or error
    """
    from app.data.mcp.executor import get_mcp_executor
    executor = get_mcp_executor()
    result = await executor.execute(input.tool_name, input.parameters)
    return result


@app.get("/mcp/tool/{tool_name}")
async def get_mcp_tool(tool_name: str):
    """Get details of a specific MCP tool."""
    from app.data.mcp.tools import get_mcp_registry
    registry = get_mcp_registry()
    tool = registry.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    return tool.to_dict()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
