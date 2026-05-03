"""
Tests for tax export endpoint.

Tests GET /tax/export
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.routers.tax import export_decisions
from datetime import datetime, timezone


@pytest.fixture
def mock_audit_repo(monkeypatch):
    """Mock audit repository."""
    from app.database.audit import AuditRepository
    repo = AsyncMock(spec=AuditRepository)

    now = datetime.now(timezone.utc)
    mock_decisions = [
        MagicMock(
            id="123e4567-e89b-12d3-a456-426614174000",
            created_at=now,
            operation_type="expense",
            description="Office supplies",
            amount=50.0,
            decision="deductible",
            confidence=0.9,
            risk_level="low",
            source="rule_engine"
        ),
        MagicMock(
            id="223e4567-e89b-12d3-a456-426614174001",
            created_at=now,
            operation_type="invoice",
            description="Consulting",
            amount=2500.0,
            decision="non_deductible",
            confidence=0.8,
            risk_level="medium",
            source="llm"
        ),
    ]
    repo.get_decisions = AsyncMock(return_value=mock_decisions)
    monkeypatch.setattr(
        "app.routers.tax.get_audit_repository",
        lambda: repo
    )
    return repo


@pytest.mark.asyncio
async def test_export_decisions_csv(mock_audit_repo):
    """Should export decisions as CSV."""
    # Mock openpyxl not installed
    with patch.dict('sys.modules', {'openpyxl': None}):
        response = await export_decisions(format="csv")
        assert response.status_code == 200
        assert response.media_type == "text/csv"
        assert "attachment" in response.headers["Content-Disposition"]
        # Check CSV content contains headers and data
        content = response.body.decode()
        assert "ID,Date,Operation,Description,Amount,Decision,Confidence,Risk,Source" in content
        assert "office supplies" in content.lower() or "consulting" in content.lower()


@pytest.mark.asyncio
async def test_export_decisions_excel_without_openpyxl(mock_audit_repo):
    """Should fallback to CSV if openpyxl not available."""
    # Simulate openpyxl import error
    with patch.dict('sys.modules', {'openpyxl': None}):
        response = await export_decisions(format="excel")
        # Should fallback to CSV because openpyxl missing
        assert response.media_type == "text/csv"


@pytest.mark.asyncio
async def test_export_decisions_with_filters(mock_audit_repo):
    """Should pass filters to repository."""
    await export_decisions(decision_type="deductible", entity_type="researcher")
    mock_audit_repo.get_decisions.assert_called_once()
    # Check that filters were passed
    call_kwargs = mock_audit_repo.get_decisions.call_args[1]
    assert call_kwargs["decision_type"] == "deductible"
    assert call_kwargs["entity_type"] == "researcher"
