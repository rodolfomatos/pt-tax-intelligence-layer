"""
Tests for AuditRepository.

Tests the audit logging and retrieval functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from app.database.audit import AuditRepository
from app.database.models import TaxDecision, AuditLog
from app.models import TaxAnalysisInput, TaxAnalysisOutput, LegalCitation, Context


def create_mock_session():
    """Create a mock DB session."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    session.added = []
    session.committed = False
    session.add = lambda obj: session.added.append(obj)
    session.flush = AsyncMock()
    session.commit = AsyncMock(side_effect=lambda: setattr(session, 'committed', True))
    session.rollback = AsyncMock()
    # execute should be an AsyncMock returning a result object (MagicMock)
    session.execute = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_get_db_session(monkeypatch):
    """Mock get_db_session to return a mock session."""
    session = create_mock_session()
    monkeypatch.setattr(
        "app.database.audit.get_db_session",
        lambda: session
    )
    return session


@pytest.fixture
def sample_input():
    """Create a sample TaxAnalysisInput."""
    return TaxAnalysisInput(
        operation_type="expense",
        description="Test expense",
        amount=100.0,
        currency="EUR",
        entity_type="researcher",
        metadata={},
        context=Context(
            project_type="FCT",
            activity_type="taxable",
            location="PT"
        )
    )


@pytest.fixture
def sample_output():
    """Create a sample TaxAnalysisOutput."""
    return TaxAnalysisOutput(
        decision="deductible",
        confidence=0.9,
        legal_basis=[LegalCitation(code="CIVA", article="20º", excerpt="Test")],
        explanation="Test decision",
        risks=[],
        assumptions=[],
        required_followup=[],
        risk_level="low",
        legal_version_timestamp=datetime.now(timezone.utc).isoformat(),
    )


@pytest.mark.asyncio
async def test_log_decision(mock_get_db_session, sample_input, sample_output):
    """Should create and save a TaxDecision."""
    repo = AuditRepository()
    result = await repo.log_decision(
        input_data=sample_input,
        output_data=sample_output,
        source="rule_engine",
        processing_time_ms=100
    )

    assert result is not None
    assert isinstance(result, TaxDecision)
    assert result.operation_type == sample_input.operation_type
    assert result.decision == sample_output.decision
    assert result.confidence == sample_output.confidence
    assert result.source == "rule_engine"
    assert result.processing_time_ms == 100
    assert len(mock_get_db_session.added) >= 1
    mock_get_db_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_log_action(mock_get_db_session):
    """Should create and save an AuditLog."""
    repo = AuditRepository()
    result = await repo.log_action(
        action="test_action",
        entity_type="tax_decision",
        entity_id="123",
        user="test-user",
        request_id="req-123",
        details={"key": "value"},
        ip_address="127.0.0.1"
    )

    assert result is not None
    assert isinstance(result, AuditLog)
    assert result.action == "test_action"
    assert result.entity_type == "tax_decision"
    assert result.user == "test-user"
    assert result.details == {"key": "value"}
    assert len(mock_get_db_session.added) >= 1


@pytest.mark.asyncio
async def test_get_decisions(mock_get_db_session):
    """Should retrieve decisions with optional filters."""
    repo = AuditRepository()
    now = datetime.now(timezone.utc)
    mock_decisions = [
        MagicMock(
            created_at=now - timedelta(days=1),
            decision="deductible"
        ),
        MagicMock(
            created_at=now - timedelta(days=2),
            decision="non_deductible"
        ),
    ]
    # Mock result.scalars().all()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = mock_decisions
    mock_get_db_session.execute.return_value = execute_result

    result = await repo.get_decisions(
        limit=10,
        offset=0,
        decision_type="deductible"
    )

    assert len(result) == 2
    mock_get_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_decisions_count(mock_get_db_session):
    """Should return count of decisions with filters."""
    repo = AuditRepository()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 5
    mock_get_db_session.execute.return_value = mock_result

    count = await repo.get_decisions_count(
        decision_type="deductible",
        entity_type="researcher"
    )

    assert count == 5
    mock_get_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_statistics(mock_get_db_session):
    """Should return aggregated statistics."""
    repo = AuditRepository()
    # Mock result.one() returning a row with attributes
    mock_row = MagicMock()
    mock_row.total = 100
    mock_row.deductible = 60
    mock_row.non_deductible = 40
    mock_row.partially_deductible = 0
    mock_row.uncertain = 0
    mock_row.avg_confidence = 0.85
    mock_result = MagicMock()
    mock_result.one.return_value = mock_row
    mock_get_db_session.execute.return_value = mock_result

    stats = await repo.get_statistics()

    assert stats["total"] == 100
    assert stats["by_decision"]["deductible"] == 60
    assert stats["by_decision"]["non_deductible"] == 40
    assert stats["avg_confidence"] == 0.85


@pytest.mark.asyncio
async def test_get_decision_by_id_found(mock_get_db_session):
    """Should retrieve decision by ID."""
    repo = AuditRepository()
    now = datetime.now(timezone.utc)
    mock_decision = MagicMock(
        id="123456",
        created_at=now,
        decision="deductible",
        confidence=0.9,
        source="rule_engine"
    )
    # Configure execute to return a result with scalar_one_or_none()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_decision
    mock_get_db_session.execute.return_value = result_mock

    result = await repo.get_decision_by_id("123456")

    assert result == mock_decision


@pytest.mark.asyncio
async def test_get_decision_by_id_not_found(mock_get_db_session):
    """Should return None when decision not found."""
    repo = AuditRepository()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_get_db_session.execute.return_value = result_mock

    result = await repo.get_decision_by_id("nonexistent")

    assert result is None
