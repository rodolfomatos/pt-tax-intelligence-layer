"""
Dashboard router.

Contains endpoints for dashboard summary and trends.
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func

from app.database.audit import get_audit_repository
from app.database.models import TaxDecision
from app.database.session import get_db_session
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def get_dashboard_summary():
    """
    Get a summary of tax decision statistics for dashboard display.

    Returns counts by decision type, risk level, entity type, and trends.
    """
    try:
        audit = get_audit_repository()
        stats = await audit.get_statistics()

        # Get recent decisions (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent = await audit.get_decisions(
            limit=100,
            offset=0,
            start_date=thirty_days_ago,
        )

        # Calculate trends
        recent_by_type = {}
        for d in recent:
            dt = d.decision
            recent_by_type[dt] = recent_by_type.get(dt, 0) + 1

        return {
            "summary": stats,
            "recent_30_days": {
                "total": len(recent),
                "by_decision": recent_by_type,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve summary")


@router.get("/trends")
async def get_dashboard_trends(
    days: int = Query(30, ge=7, le=365),
    group_by: str = Query("day", description="Group by: day, week, month"),
):
    """
    Get decision trends over time.

    Args:
        days: Number of days to look back
        group_by: Time grouping (day, week, month)

    Returns trend data for charting.
    """
    try:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        async with get_db_session() as session:
            # Group by date
            if group_by == "week":
                date_trunc = func.date_trunc("week", TaxDecision.created_at)
            elif group_by == "month":
                date_trunc = func.date_trunc("month", TaxDecision.created_at)
            else:
                date_trunc = func.date_trunc("day", TaxDecision.created_at)

            query = (
                select(
                    date_trunc.label("period"),
                    TaxDecision.decision,
                    func.count(TaxDecision.id).label("count"),
                )
                .where(TaxDecision.created_at >= start_date)
                .group_by("period", TaxDecision.decision)
                .order_by("period")
            )

            result = await session.execute(query)
            rows = result.all()

            # Format for charting
            trends = {}
            for row in rows:
                period = row.period.isoformat()
                if period not in trends:
                    trends[period] = {}
                trends[period][row.decision] = row.count

            return {
                "days": days,
                "group_by": group_by,
                "trends": [{"period": k, **v} for k, v in trends.items()],
            }
    except Exception as e:
        logger.error(f"Failed to get trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trends")
