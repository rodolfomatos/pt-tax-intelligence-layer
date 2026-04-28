"""
Search and legislation router.

Contains endpoints for searching legislation and retrieving articles.
"""

from fastapi import APIRouter, Query, HTTPException
from app.data.ptdata.client import get_ptdata_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tax", tags=["Search"])


@router.get("/search")
async def search_legislation(
    q: str = Query(..., description="Search query"),
    code: str = Query(None, description="Law code (e.g., CIVA, CIRC)"),
    limit: int = Query(10, ge=1, le=100),
):
    """
    Search Portuguese tax legislation.

    Searches across multiple sources:
    - ptdata API (primary source)
    - Cache (for recent queries)

    Args:
        q: Search query (e.g., "deduções", "IVA")
        code: Filter by law code
        limit: Maximum number of results

    Returns:
        List of matching legislation articles
    """
    try:
        ptdata = await get_ptdata_client()
        results = await ptdata.search_legislation(q, code=code, limit=limit)
        return {"query": q, "code": code, "results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/article/{code}/{article}")
async def get_article(code: str, article: str):
    """
    Retrieve a specific tax law article.

    Fetches the full text and metadata for a specific article.

    Args:
        code: Law code (e.g., CIVA, CIRC)
        article: Article number (e.g., "20", "20º")

    Returns:
        Article details with content and metadata
    """
    try:
        ptdata = await get_ptdata_client()
        article_data = await ptdata.get_article(code, article)

        if not article_data:
            raise HTTPException(
                status_code=404, detail=f"Article not found: {code} {article}"
            )

        return article_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get article: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve article")
