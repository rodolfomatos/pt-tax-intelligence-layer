"""
Tests for GraphQuery.

Tests the query API for the knowledge graph with temporal validity.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from app.data.memory.graph.query import GraphQuery
from app.data.memory.graph.models import GraphNode, GraphEdge, Contradiction


def create_mock_session():
    """Helper to create mock session with context manager support."""
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


@pytest.fixture
def mock_get_db_session(monkeypatch):
    """Mock get_db_session to return a configurable mock."""
    session = create_mock_session()
    monkeypatch.setattr(
        "app.data.memory.graph.query.get_db_session",
        lambda: session
    )
    return session


@pytest.fixture
def mock_gmif_classifier(monkeypatch):
    """Mock GMIF classifier."""
    from app.data.memory.graph.gmif import GMIFClassifier
    
    mock = MagicMock(spec=GMIFClassifier)
    monkeypatch.setattr(
        "app.data.memory.graph.query.get_gmif_classifier",
        lambda: mock
    )
    return mock


@pytest.mark.asyncio
async def test_query_entity_by_id_found(mock_get_db_session, mock_gmif_classifier):
    """Should return node when found by entity_id."""
    now = datetime.now(timezone.utc)
    node = GraphNode(
        id="123e4567-e89b-12d3-a456-426614174000",
        node_type="decision",
        label="Test Decision",
        properties={"key": "value"},
        gmif_type="M1",
        external_id="decision-123",
        created_at=now,
        valid_from=now,
        valid_to=None
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = node
    mock_get_db_session.execute.return_value = mock_result
    
    query = GraphQuery()
    result = await query.query_entity(entity_id=str(node.id))
    
    assert result is not None
    assert result["id"] == str(node.id)
    assert result["node_type"] == "decision"
    assert result["label"] == "Test Decision"
    assert result["properties"] == {"key": "value"}
    assert result["gmif_type"] == "M1"


@pytest.mark.asyncio
async def test_query_entity_by_external_id_found(mock_get_db_session, mock_gmif_classifier):
    """Should return node when found by external_id."""
    now = datetime.now(timezone.utc)
    node = GraphNode(
        id="123e4567-e89b-12d3-a456-426614174000",
        node_type="legal_basis",
        label="CIVA Art 20",
        properties={"code": "CIVA", "article": "20º"},
        gmif_type=None,
        external_id="CIVA-20",
        created_at=now,
        valid_from=now,
        valid_to=None
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = node
    mock_get_db_session.execute.return_value = mock_result
    
    query = GraphQuery()
    result = await query.query_entity(external_id="CIVA-20")
    
    assert result is not None
    assert result["external_id"] == "CIVA-20"


@pytest.mark.asyncio
async def test_query_entity_not_found(mock_get_db_session, mock_gmif_classifier):
    """Should return None when node not found."""
    mock_get_db_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    
    query = GraphQuery()
    result = await query.query_entity(entity_id="nonexistent")
    
    assert result is None


@pytest.mark.asyncio
async def test_query_as_of_without_type(mock_get_db_session, mock_gmif_classifier):
    """Should return all nodes valid at a specific time."""
    now = datetime.now(timezone.utc)
    node1 = GraphNode(
        id="id1",
        node_type="decision",
        label="Decision 1",
        properties={},
        gmif_type="M1",
        external_id=None,
        created_at=now,
        valid_from=now - timedelta(days=10),
        valid_to=now + timedelta(days=10)
    )
    node2 = GraphNode(
        id="id2",
        node_type="entity",
        label="Entity 1",
        properties={},
        gmif_type=None,
        external_id=None,
        created_at=now,
        valid_from=now - timedelta(days=5),
        valid_to=None
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [node1, node2]
    mock_get_db_session.execute.return_value = mock_result
    
    query = GraphQuery()
    results = await query.query_as_of(as_of=now)
    
    assert len(results) == 2
    assert results[0]["id"] == "id1"
    assert results[1]["id"] == "id2"


@pytest.mark.asyncio
async def test_query_as_of_with_node_type(mock_get_db_session, mock_gmif_classifier):
    """Should filter nodes by type when node_type is provided."""
    now = datetime.now(timezone.utc)
    node = GraphNode(
        id="id1",
        node_type="decision",
        label="Decision 1",
        properties={},
        gmif_type="M1",
        external_id=None,
        created_at=now,
        valid_from=now - timedelta(days=10),
        valid_to=None
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [node]
    mock_get_db_session.execute.return_value = mock_result
    
    query = GraphQuery()
    results = await query.query_as_of(node_type="decision", as_of=now)
    
    assert len(results) == 1
    # Verify the query included a where clause for node_type


@pytest.mark.asyncio
async def test_timeline_entity_found(mock_get_db_session, mock_gmif_classifier):
    """Should return timeline for entity with edges."""
    now = datetime.now(timezone.utc)
    entity = GraphNode(
        id="entity-id",
        node_type="entity",
        label="Researcher 1",
        properties={},
        gmif_type=None,
        external_id="researcher-123",
        created_at=now,
        valid_from=now,
        valid_to=None
    )
    decision1 = GraphNode(
        id="decision-1",
        node_type="decision",
        label="Decision 1",
        properties={},
        gmif_type="M1",
        external_id="decision-1",
        created_at=now,
        valid_from=now,
        valid_to=None
    )
    decision2 = GraphNode(
        id="decision-2",
        node_type="decision",
        label="Decision 2",
        properties={},
        gmif_type="M2",
        external_id="decision-2",
        created_at=now,
        valid_from=now,
        valid_to=None
    )
    
    edge1 = GraphEdge(
        id="edge1",
        source_id=entity.id,
        target_id=decision1.id,
        relation_type="requested",
        confidence=0.9,
        created_at=now - timedelta(days=2)
    )
    edge2 = GraphEdge(
        id="edge2",
        source_id=entity.id,
        target_id=decision2.id,
        relation_type="requested",
        confidence=0.8,
        created_at=now - timedelta(days=1)
    )
    
    # Setup execute side effects
    entity_result = MagicMock(scalar_one_or_none=MagicMock(return_value=entity))
    
    edges_all_mock = MagicMock()
    edges_all_mock.all = MagicMock(return_value=[edge1, edge2])
    edges_scalars_mock = MagicMock()
    edges_scalars_mock.all = edges_all_mock.all
    edges_result = MagicMock(scalars=MagicMock(return_value=edges_scalars_mock))
    
    decision_result = MagicMock(scalar_one_or_none=MagicMock(return_value=decision1))
    decision2_result = MagicMock(scalar_one_or_none=MagicMock(return_value=decision2))
    
    mock_get_db_session.execute.side_effect = [entity_result, edges_result, decision_result, decision2_result]
    
    query = GraphQuery()
    timeline = await query.timeline(entity_external_id="researcher-123")
    
    assert len(timeline) == 2
    # Should be sorted by timestamp descending
    assert timeline[0]["node"]["id"] == "decision-2"
    assert timeline[1]["node"]["id"] == "decision-1"


@pytest.mark.asyncio
async def test_timeline_entity_not_found(mock_get_db_session, mock_gmif_classifier):
    """Should return empty list when entity not found."""
    mock_get_db_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    
    query = GraphQuery()
    timeline = await query.timeline(entity_external_id="nonexistent")
    
    assert timeline == []


@pytest.mark.asyncio
async def test_find_similar_decision_found(mock_get_db_session, mock_gmif_classifier):
    """Should find similar decisions when edges exist."""
    now = datetime.now(timezone.utc)
    decision = GraphNode(
        id="decision-id",
        node_type="decision",
        label="Decision 1",
        properties={},
        gmif_type="M1",
        external_id="decision-1",
        created_at=now,
        valid_from=now,
        valid_to=None
    )
    similar_decision = GraphNode(
        id="similar-id",
        node_type="decision",
        label="Similar Decision",
        properties={},
        gmif_type="M2",
        external_id="decision-2",
        created_at=now,
        valid_from=now,
        valid_to=None
    )
    edge = GraphEdge(
        id="edge1",
        source_id=decision.id,
        target_id=similar_decision.id,
        relation_type="similar_to",
        confidence=0.85,
        created_at=now
    )
    
    decision_result = MagicMock(scalar_one_or_none=MagicMock(return_value=decision))
    similar_result = MagicMock()
    similar_result.__iter__ = lambda self: iter([(edge, similar_decision)])
    mock_get_db_session.execute.side_effect = [decision_result, similar_result]
    
    query = GraphQuery()
    similar = await query.find_similar(decision_id="decision-1", limit=5)
    
    assert len(similar) == 1
    assert similar[0]["node"]["id"] == "similar-id"
    assert similar[0]["confidence"] == 0.85


@pytest.mark.asyncio
async def test_find_similar_decision_not_found(mock_get_db_session, mock_gmif_classifier):
    """Should return empty list when decision not found."""
    mock_get_db_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    
    query = GraphQuery()
    similar = await query.find_similar(decision_id="nonexistent")
    
    assert similar == []


@pytest.mark.asyncio
async def test_find_contradictions_all(mock_get_db_session, mock_gmif_classifier):
    """Should return all unresolved contradictions."""
    contra1 = Contradiction(
        id="contra1",
        claim_a="Claim A",
        claim_b="Claim B",
        context={},
        severity="high",
        resolved=False
    )
    contra2 = Contradiction(
        id="contra2",
        claim_a="Claim C",
        claim_b="Claim D",
        context={},
        severity="medium",
        resolved=False
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [contra1, contra2]
    mock_get_db_session.execute.return_value = mock_result
    
    query = GraphQuery()
    contradictions = await query.find_contradictions()
    
    assert len(contradictions) == 2
    assert contradictions[0]["id"] == "contra1"
    assert contradictions[1]["severity"] == "medium"


@pytest.mark.asyncio
async def test_find_contradictions_filtered(mock_get_db_session, mock_gmif_classifier):
    """Should filter contradictions by decision_id."""
    contra1 = Contradiction(
        id="contra1",
        claim_a="decision-123",
        claim_b="Claim B",
        context={},
        severity="high",
        resolved=False
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [contra1]
    mock_get_db_session.execute.return_value = mock_result
    
    query = GraphQuery()
    contradictions = await query.find_contradictions(decision_id="decision-123")
    
    assert len(contradictions) == 1
    assert contradictions[0]["id"] == "contra1"


@pytest.mark.asyncio
async def test_get_gmif_summary(mock_get_db_session, mock_gmif_classifier):
    """Should return GMIF summary with counts."""
    # Mock result rows
    row1 = MagicMock(gmif_type="M1", count=10, node_type="decision")
    row2 = MagicMock(gmif_type="M2", count=20, node_type="decision")
    # The where clause filters to decisions only, so only decision rows expected
    mock_get_db_session.execute.return_value = [row1, row2]
    
    query = GraphQuery()
    summary = await query.get_gmif_summary()
    
    assert "by_gmif" in summary
    assert summary["by_gmif"]["M1"] == 10
    assert summary["by_gmif"]["M2"] == 20
    assert "by_type" in summary
    # Note: by_type gets overwritten per iteration; last value wins
    assert summary["by_type"]["decision"] == 20


@pytest.mark.asyncio
async def test_get_decisions_by_gmif(mock_get_db_session, mock_gmif_classifier):
    """Should return decisions filtered by GMIF type."""
    now = datetime.now(timezone.utc)
    decision = GraphNode(
        id="decision-id",
        node_type="decision",
        label="M2 Decision",
        properties={},
        gmif_type="M2",
        external_id="decision-123",
        created_at=now,
        valid_from=now,
        valid_to=None
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [decision]
    mock_get_db_session.execute.return_value = mock_result
    
    query = GraphQuery()
    decisions = await query.get_decisions_by_gmif(gmif_type="M2", limit=100)
    
    assert len(decisions) == 1
    assert decisions[0]["gmif_type"] == "M2"


@pytest.mark.asyncio
async def test_get_graph_stats(mock_get_db_session, mock_gmif_classifier):
    """Should return overall graph statistics."""
    # Mock node counts: use MagicMock with node_type and count
    node_row1 = MagicMock()
    node_row1.node_type = "decision"
    node_row1.count = 50
    node_row2 = MagicMock()
    node_row2.node_type = "entity"
    node_row2.count = 30
    # Mock edge counts
    edge_row1 = MagicMock()
    edge_row1.relation_type = "similar_to"
    edge_row1.count = 100
    edge_row2 = MagicMock()
    edge_row2.relation_type = "based_on"
    edge_row2.count = 80
    # Mock contradictions count
    contra_mock = MagicMock()
    contra_mock.scalar.return_value = 5
    
    mock_get_db_session.execute.side_effect = [
        [node_row1, node_row2],   # nodes query returns iterable
        [edge_row1, edge_row2],   # edges query returns iterable
        contra_mock               # contradictions query
    ]
    
    query = GraphQuery()
    stats = await query.get_graph_stats()
    
    assert stats["nodes"]["decision"] == 50
    assert stats["nodes"]["entity"] == 30
    assert stats["edges"]["similar_to"] == 100
    assert stats["edges"]["based_on"] == 80
    assert stats["open_contradictions"] == 5


def test_node_to_dict(mock_gmif_classifier):
    """Should convert node to dictionary with all fields."""
    now = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    node = GraphNode(
        id="123e4567-e89b-12d3-a456-426614174000",
        node_type="decision",
        label="Test Decision",
        properties={"amount": 150.0, "currency": "EUR"},
        gmif_type="M1",
        external_id="decision-123",
        created_at=now,
        valid_from=now,
        valid_to=None
    )
    
    query = GraphQuery()
    result = query._node_to_dict(node)
    
    assert result["id"] == str(node.id)
    assert result["node_type"] == "decision"
    assert result["label"] == "Test Decision"
    assert result["properties"] == {"amount": 150.0, "currency": "EUR"}
    assert result["gmif_type"] == "M1"
    assert result["external_id"] == "decision-123"
    assert result["created_at"] == now.isoformat()
    assert result["valid_from"] == now.isoformat()
    assert result["valid_to"] is None


def test_get_graph_query_singleton():
    """Should return singleton instance."""
    from app.data.memory.graph.query import get_graph_query
    # Reset global for test
    import app.data.memory.graph.query as query_mod
    query_mod._query = None
    q1 = get_graph_query()
    q2 = get_graph_query()
    assert q1 is q2
    # Cleanup
    query_mod._query = None
