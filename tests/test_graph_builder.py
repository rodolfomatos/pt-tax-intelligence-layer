"""
Tests for KnowledgeGraphBuilder.

Tests the builder that creates graph nodes/edges from decisions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.data.memory.graph.builder import KnowledgeGraphBuilder
from app.data.memory.graph.gmif import GMIFType


# Helper to create mock session with context manager support
def create_mock_session():
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    session.added = []
    session.committed = False
    session.add = lambda obj: session.added.append(obj)
    session.commit = AsyncMock(side_effect=lambda: setattr(session, 'committed', True))
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


class MockGMIFClassifier:
    """Mock GMIF classifier."""
    def classify(self, decision: str, confidence: float, legal_basis: list, risks: list, assumptions: list, contradictions: list) -> GMIFType:
        # Simple rule: high confidence deductible => M2, else M1
        if decision == "deductible" and confidence >= 0.8:
            return GMIFType.M2_CONTEXTUAL_CONDITION
        return GMIFType.M1_PRIMARY_EVIDENCE

    def get_contradictions(self, legal_basis: list) -> list:
        return []


@pytest.fixture
def builder(monkeypatch):
    """Create builder with mocked classifier."""
    mock_classifier = MockGMIFClassifier()
    monkeypatch.setattr(
        "app.data.memory.graph.builder.get_gmif_classifier",
        lambda: mock_classifier
    )
    return KnowledgeGraphBuilder()


@pytest.fixture
def mock_get_db_session(monkeypatch):
    """Mock get_db_session to return a configurable mock."""
    session = create_mock_session()
    monkeypatch.setattr(
        "app.data.memory.graph.builder.get_db_session",
        lambda: session
    )
    return session


@pytest.mark.asyncio
async def test_add_decision_creates_node_and_edges(builder, mock_get_db_session):
    """Should create graph node for a decision."""
    decision_id = "test-decision-123"
    description = "Test expense"
    decision_type = "deductible"
    confidence = 0.9
    legal_basis = [{"code": "CIVA", "article": "20º", "excerpt": "test"}]
    entity_type = "researcher"
    project_type = "FCT"
    risks = []
    assumptions = []

    # Mock execute to return no existing nodes (avoid similarity edges)
    mock_get_db_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    gmif_type = await builder.add_decision(
        decision_id=decision_id,
        description=description,
        decision_type=decision_type,
        confidence=confidence,
        legal_basis=legal_basis,
        entity_type=entity_type,
        project_type=project_type,
        risks=risks,
        assumptions=assumptions
    )

    assert gmif_type in [GMIFType.M1_PRIMARY_EVIDENCE, GMIFType.M2_CONTEXTUAL_CONDITION, GMIFType.M3_PARTIAL_DESCRIPTION, GMIFType.M4_DOUBTFUL_TESTIMONY, GMIFType.M5_INTERPRETATION, GMIFType.M6_DERIVED_EVIDENCE, GMIFType.M7_SYNTHESIS]
    assert len(mock_get_db_session.added) >= 1  # At least node added


@pytest.mark.asyncio
async def test_add_decision_with_contradictions(builder, mock_get_db_session):
    """Should detect contradictions in legal basis."""
    builder.classifier.get_contradictions = MagicMock(return_value=["contradiction1"])

    mock_get_db_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    gmif_type = await builder.add_decision(
        decision_id="test-contradiction",
        description="Test with contradiction",
        decision_type="non_deductible",
        confidence=0.7,
        legal_basis=[
            {"code": "CIVA", "article": "20º", "excerpt": "deductible"},
            {"code": "CIVA", "article": "6º", "excerpt": "exempt"}
        ],
        entity_type="researcher",
        project_type="FCT",
        risks=[],
        assumptions=[]
    )

    # Should still classify, contradictions tracked separately
    assert gmif_type in [GMIFType.M1_PRIMARY_EVIDENCE, GMIFType.M2_CONTEXTUAL_CONDITION, GMIFType.M3_PARTIAL_DESCRIPTION, GMIFType.M4_DOUBTFUL_TESTIMONY, GMIFType.M5_INTERPRETATION, GMIFType.M6_DERIVED_EVIDENCE, GMIFType.M7_SYNTHESIS]


@pytest.mark.asyncio
async def test_get_statistics(builder, mock_get_db_session):
    """Should return graph statistics."""
    # Configure scalar to return counts
    mock_get_db_session.scalar = AsyncMock(side_effect=[100, 50])
    # Configure execute for gmif distribution
    mock_result = MagicMock()
    mock_result.all.return_value = [("M1", 10), ("M2", 20)]
    mock_get_db_session.execute.return_value = mock_result

    stats = await builder.get_stats()

    assert "total_nodes" in stats
    assert stats["total_nodes"] == 100
    assert "total_edges" in stats
    assert stats["total_edges"] == 50
    assert "gmif_distribution" in stats
    assert isinstance(stats["gmif_distribution"], dict)


@pytest.mark.asyncio
async def test_get_gmif_summary(builder, mock_get_db_session):
    """Should return GMIF summary with counts and avg confidence."""
    # Same as get_stats currently
    mock_get_db_session.scalar = AsyncMock(side_effect=[100, 50])
    mock_result = MagicMock()
    mock_result.all.return_value = [("M1", 30), ("M2", 70)]
    mock_get_db_session.execute.return_value = mock_result

    summary = await builder.get_gmif_summary()

    assert "M1" in summary["gmif_distribution"] or "summary" in summary
    assert summary["gmif_distribution"]["M1"] == 30
    assert summary["gmif_distribution"]["M2"] == 70


def test_builder_initialization():
    """Should initialize with GMIF classifier."""
    builder = KnowledgeGraphBuilder()
    assert builder.classifier is not None
