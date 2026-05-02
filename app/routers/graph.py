"""
Graph and GMIF router.

Contains endpoints for knowledge graph, GMIF classification, and visualization.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from app.data.memory.graph.builder import get_graph_builder
from app.database.audit import get_audit_repository
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tax/graph", tags=["Knowledge Graph"])


@router.get("/stats")
async def get_graph_stats():
    """Get knowledge graph statistics."""
    try:
        builder = get_graph_builder()
        stats = await builder.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get graph stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve graph stats")


@router.get("/gmif-summary")
async def get_gmif_summary():
    """Get GMIF classification summary across all decisions."""
    try:
        builder = get_graph_builder()
        summary = await builder.get_gmif_summary()
        return summary
    except Exception as e:
        logger.error(f"Failed to get GMIF summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve GMIF summary")


@router.get("/by-gmif/{gmif_type}")
async def get_decisions_by_gmif(gmif_type: str, limit: int = 100):
    """Get decisions by GMIF classification type."""
    try:
        builder = get_graph_builder()
        decisions = await builder.get_decisions_by_gmif(gmif_type, limit=limit)
        return {"gmif_type": gmif_type, "count": len(decisions), "decisions": decisions}
    except Exception as e:
        logger.error(f"Failed to get decisions by GMIF: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve decisions")


@router.get("/contradictions")
async def get_contradictions(decision_id: Optional[str] = None):
    """Find contradictory decisions in the knowledge graph."""
    try:
        builder = get_graph_builder()
        contradictions = await builder.find_contradictions(decision_id)
        return {"count": len(contradictions), "contradictions": contradictions}
    except Exception as e:
        logger.error(f"Failed to find contradictions: {e}")
        raise HTTPException(status_code=500, detail="Failed to find contradictions")


@router.get("/timeline/{entity_external_id}")
async def get_timeline(entity_external_id: str):
    """Get decision timeline for a specific entity."""
    try:
        audit = get_audit_repository()
        decisions = await audit.get_decisions(
            limit=100,
            offset=0,
            entity_type=entity_external_id,
        )

        timeline = [
            {
                "date": d.created_at.isoformat(),
                "decision": d.decision,
                "confidence": d.confidence,
                "description": d.description,
            }
            for d in decisions
        ]

        return {
            "entity": entity_external_id,
            "count": len(timeline),
            "timeline": timeline,
        }
    except Exception as e:
        logger.error(f"Failed to get timeline: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve timeline")
