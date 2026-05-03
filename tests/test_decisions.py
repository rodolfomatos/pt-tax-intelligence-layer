"""
Tests for decisions router endpoints.

Tests: /tax/decisions, /tax/statistics, /tax/history/{decision_id}
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from app.routers.decisions import get_decisions, get_statistics, get_decision_history


@pytest.fixture
def mock_audit_repo(monkeypatch):
    """Mock audit repository used by decisions router."""
    from app.database.audit import AuditRepository
    repo = AsyncMock(spec=AuditRepository)

    # Set up default returns
    now = datetime.now(timezone.utc)
    mock_decisions = [
        MagicMock(
            id="123e4567-e89b-12d3-a456-426614174000",
            created_at=now - timedelta(days=1),
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
            created_at=now - timedelta(days=2),
            operation_type="invoice",
            description="Consulting",
            amount=2500.0,
            decision="non_deductible",
            confidence=0.8,
            risk_level="medium",
            source="llm"
        ),
    ]
    repo.get_decisions.return_value = mock_decisions
    repo.get_decisions_count.return_value = len(mock_decisions)
    repo.get_statistics.return_value = {
        "total": 100,
        "by_decision": {"deductible": 60, "non_deductible": 40},
        "avg_confidence": 0.85,
    }
    repo.get_decision_by_id.return_value = MagicMock(
        id="123e4567-e89b-12d3-a456-426614174000",
        created_at=now,
        decision="deductible",
        confidence=0.9,
        source="rule_engine"
    )

    # Patch the function in the decisions module
    monkeypatch.setattr(
        "app.routers.decisions.get_audit_repository",
        lambda: repo
    )
    return repo


@pytest.mark.asyncio
async def test_get_decisions_success(mock_audit_repo):
    """Should return list of decisions with pagination."""
    result = await get_decisions(limit=100, offset=0)

    assert "decisions" in result
    assert len(result["decisions"]) == 2
    assert result["total"] == 2
    assert result["limit"] == 100
    assert result["offset"] == 0
    # Check decision fields from the configured mock
    assert result["decisions"][0]["decision"] == "deductible"
    assert "id" in result["decisions"][0]


@pytest.mark.asyncio
async def test_get_decisions_with_filters(mock_audit_repo):
    """Should pass filters to repository."""
    await get_decisions(
        limit=50,
        offset=10,
        decision_type="deductible",
        entity_type="researcher"
    )

    mock_audit_repo.get_decisions.assert_called_once()
    call_kwargs = mock_audit_repo.get_decisions.call_args[1]
    assert call_kwargs["limit"] == 50
    assert call_kwargs["offset"] == 10
    assert call_kwargs["decision_type"] == "deductible"
    assert call_kwargs["entity_type"] == "researcher"

    mock_audit_repo.get_decisions_count.assert_called_once()


@pytest.mark.asyncio
async def test_get_decisions_error(mock_audit_repo):
    """Should raise HTTPException on error."""
    mock_audit_repo.get_decisions.side_effect = Exception("DB error")

    with pytest.raises(HTTPException) as exc_info:
        await get_decisions()
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_get_statistics_success(mock_audit_repo):
    """Should return statistics."""
    mock_audit_repo.get_statistics.return_value = {
        "total": 100,
        "by_decision": {"deductible": 60, "non_deductible": 40},
        "avg_confidence": 0.85,
    }

    result = await get_statistics()

    assert result["total"] == 100
    assert result["by_decision"]["deductible"] == 60
    mock_audit_repo.get_statistics.assert_called_once()


@pytest.mark.asyncio
async def test_get_statistics_error(mock_audit_repo):
    """Should raise HTTPException on error."""
    mock_audit_repo.get_statistics.side_effect = Exception("DB error")

    with pytest.raises(HTTPException) as exc_info:
        await get_statistics()
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_get_decision_history_found(mock_audit_repo):
    """Should return decision history."""
    now = datetime.now(timezone.utc)
    decision = MagicMock(
        id="123e4567-e89b-12d3-a456-426614174000",
        created_at=now,
        decision="deductible",
        confidence=0.9,
        source="rule_engine"
    )
    mock_audit_repo.get_decision_by_id.return_value = decision

    result = await get_decision_history(decision_id=str(decision.id))

    assert result["decision_id"] == str(decision.id)
    assert "original" in result
    assert result["original"]["decision"] == "deductible"
    assert "history" in result
    assert "related_actions" in result


@pytest.mark.asyncio
async def test_get_decision_history_not_found(mock_audit_repo):
    """Should raise 404 when decision not found."""
    mock_audit_repo.get_decision_by_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await get_decision_history(decision_id="nonexistent")
    assert exc_info.value.status_code == 404
    assert "Decision not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_decision_history_error(mock_audit_repo):
    """Should raise 500 on unexpected error."""
    mock_audit_repo.get_decision_by_id.side_effect = Exception("DB error")

    with pytest.raises(HTTPException) as exc_info:
        await get_decision_history(decision_id="test-id")
    assert exc_info.value.status_code == 500
