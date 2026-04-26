from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
import logging
import time
from typing import Optional
from datetime import datetime

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
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("UP Tax Intelligence Layer starting...")
    
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
    
    yield
    
    logger.info("UP Tax Intelligence Layer shutting down...")
    
    # Cleanup
    ptdata = await get_ptdata_client()
    await ptdata.close()
    
    cache = await get_cache_client()
    await cache.close()
    
    await close_db()


app = FastAPI(
    title="UP Tax Intelligence Layer",
    description="Backend decision engine for Portuguese tax law analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_per_minute,
    requests_per_hour=settings.rate_limit_per_hour,
    burst_limit=settings.rate_limit_burst,
)

if settings.api_key:
    app.add_middleware(APIKeyMiddleware)

app.include_router(graph_viz_router)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Verifies connectivity to ptdata API and Redis cache.
    Returns overall system status and dependency states.
    """
    ptdata = await get_ptdata_client()
    cache = await get_cache_client()
    
    ptdata_status = "ok" if await ptdata.health_check() else "unavailable"
    cache_status = "ok" if await cache.health_check() else "unavailable"
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        dependencies={
            "ptdata": ptdata_status,
            "database": "ok",
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
