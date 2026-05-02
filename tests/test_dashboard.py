"""
Tests for dashboard router.

Tests endpoints: /dashboard/summary, /dashboard/trends
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from app.routers.dashboard import get_dashboard_summary, get_dashboard_trends


def create_mock_session():
    """Create a mock DB session that supports async context manager and execute."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    # session.commit, rollback, add etc. if needed
    return session


@pytest.fixture
def mock_audit_repo(monkeypatch):
    """Mock audit repository."""
    from app.database.audit import AuditRepository
    repo = AsyncMock(spec=AuditRepository)
    repo.get_statistics.return_value = {
        "total": 100,
        "by_decision": {
            "deductible": 60,
            "non_deductible": 20,
            "partially_deductible": 10,
            "uncertain": 10
        },
        "avg_confidence": 0.85
    }
    now = datetime.now(timezone.utc)
    repo.get_decisions.return_value = [
        MagicMock(decision='deductible', created_at=now - timedelta(days=i))
        for i in range(1, 6)
    ]
    monkeypatch.setattr(
        "app.routers.dashboard.get_audit_repository",
        lambda: repo
    )
    return repo


@pytest.fixture
def mock_db_session(monkeypatch):
    """Mock get_db_session to return a mock session."""
    session = create_mock_session()
    monkeypatch.setattr(
        "app.routers.dashboard.get_db_session",
        lambda: session
    )
    return session


@pytest.mark.asyncio
async def test_get_dashboard_summary_success(mock_audit_repo):
    """Should return summary with stats and recent decisions."""
    response = await get_dashboard_summary()
    assert "summary" in response
    assert "recent_30_days" in response
    assert "generated_at" in response
    assert response["summary"]["total"] == 100
    mock_audit_repo.get_statistics.assert_called_once()
    mock_audit_repo.get_decisions.assert_called_once()


@pytest.mark.asyncio
async def test_get_dashboard_summary_error(mock_audit_repo):
    """Should raise HTTPException on error."""
    from fastapi import HTTPException
    mock_audit_repo.get_statistics.side_effect = Exception("DB error")
    with pytest.raises(HTTPException) as exc_info:
        await get_dashboard_summary()
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_get_dashboard_trends_with_db(mock_audit_repo, mock_db_session):
    """Should return trends with data from query."""
    # Configure execute to return rows
    rows = [
        MagicMock(period=datetime(2024, 1, 1, tzinfo=timezone.utc), decision='deductible', count=5),
        MagicMock(period=datetime(2024, 1, 2, tzinfo=timezone.utc), decision='non_deductible', count=3),
    ]
    mock_result = MagicMock()
    mock_result.all.return_value = rows
    mock_db_session.execute.return_value = mock_result

    response = await get_dashboard_trends(days=30, group_by="day")
    assert "days" in response
    assert response["days"] == 30
    assert "group_by" in response
    assert response["group_by"] == "day"
    assert "trends" in response
    assert isinstance(response["trends"], list)
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_dashboard_trends_week_grouping(mock_audit_repo, mock_db_session):
    """Should use week grouping."""
    rows = []
    mock_result = MagicMock()
    mock_result.all.return_value = rows
    mock_db_session.execute.return_value = mock_result

    response = await get_dashboard_trends(days=14, group_by="week")
    assert response["group_by"] == "week"


@pytest.mark.asyncio
async def test_get_dashboard_trends_month_grouping(mock_audit_repo, mock_db_session):
    """Should use month grouping."""
    rows = []
    mock_result = MagicMock()
    mock_result.all.return_value = rows
    mock_db_session.execute.return_value = mock_result

    response = await get_dashboard_trends(days=90, group_by="month")
    assert response["group_by"] == "month"


@pytest.mark.asyncio
async def test_get_dashboard_trends_empty_results(mock_audit_repo, mock_db_session):
    """Should handle empty query results gracefully."""
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db_session.execute.return_value = mock_result

    response = await get_dashboard_trends(days=30)
    assert response["trends"] == []


@pytest.mark.asyncio
async def test_get_dashboard_trends_db_error(mock_audit_repo, mock_db_session):
    """Should raise HTTPException on database error."""
    from fastapi import HTTPException
    mock_db_session.execute.side_effect = Exception("DB error")
    with pytest.raises(HTTPException) as exc_info:
        await get_dashboard_trends(days=30)
    assert exc_info.value.status_code == 500
