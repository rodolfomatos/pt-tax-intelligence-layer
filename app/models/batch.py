"""
Batch processing for tax analysis.

Allows analyzing multiple tax operations in a single request.
"""

from pydantic import BaseModel
from typing import List
from app.models import TaxAnalysisInput, TaxAnalysisOutput


class BatchAnalysisRequest(BaseModel):
    """Request for batch tax analysis."""

    items: List[TaxAnalysisInput]
    stop_on_error: bool = False


class BatchAnalysisResponse(BaseModel):
    """Response for batch tax analysis."""

    total: int
    successful: int
    failed: int
    results: List[TaxAnalysisOutput]
    errors: List[dict] = []
