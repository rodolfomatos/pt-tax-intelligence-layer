"""
Decisions router.

Contains endpoints for listing, searching, and retrieving decisions.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime

from app.database.audit import get_audit_repository
from app.models import TaxAnalysisOutput
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tax", tags=["Decisions"])


@router.get("/decisions")
async def get_decisions(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    decision_type: Optional[str] = Query(None, description="Filter by decision type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
):
    """
    Get past decisions with pagination and optional filters.
    """
    try:
        audit = get_audit_repository()
        decisions = await audit.get_decisions(
            limit=limit,
            offset=offset,
            decision_type=decision_type,
            entity_type=entity_type,
            start_date=start_date,
            end_date=end_date,
        )
        total = await audit.get_decisions_count(
            decision_type=decision_type,
            entity_type=entity_type,
            start_date=start_date,
            end_date=end_date,
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


@router.get("/statistics")
async def get_statistics():
    """Get decision statistics."""
    try:
        audit = get_audit_repository()
        stats = await audit.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.get("/history/{decision_id}")
async def get_decision_history(decision_id: str):
    """
    Get historical changes for a specific decision.

    Tracks how a decision evolved over time (if it was re-evaluated).
    """
    try:
        audit = get_audit_repository()
        decision = await audit.get_decision_by_id(decision_id)

        if not decision:
            raise HTTPException(status_code=404, detail="Decision not found")

        # Get related audit logs
        # This would track re-evaluations, validations, etc.
        return {
            "decision_id": str(decision.id),
            "original": {
                "created_at": decision.created_at.isoformat(),
                "decision": decision.decision,
                "confidence": decision.confidence,
                "source": decision.source,
            },
            "history": [],  # Would contain re-evaluations
            "related_actions": [],  # Would contain validation, etc.
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")
