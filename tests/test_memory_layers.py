"""
Tests for MemoryLayers.

Tests the layered memory system (L0-L3).
"""

import pytest
from unittest.mock import MagicMock
from app.data.memory.layers import MemoryLayers, get_memory_layers
from app.data.memory.semantic import SemanticMemory


@pytest.fixture
def mock_semantic(monkeypatch):
    """Mock SemanticMemory."""
    mock = MagicMock(spec=SemanticMemory)
    mock.add_decision = MagicMock()
    mock.search = MagicMock(return_value=[{"id": "1", "score": 0.9}])
    monkeypatch.setattr("app.data.memory.layers.get_semantic_memory", lambda: mock)
    return mock


@pytest.fixture
def memory_layers(mock_semantic):
    """Create MemoryLayers with mocked semantic."""
    return MemoryLayers()


def test_get_memory_layers_singleton():
    """Should return singleton instance."""
    l1 = get_memory_layers()
    l2 = get_memory_layers()
    assert l1 is l2


def test_l0_identity(memory_layers):
    """Should return L0 identity."""
    identity = memory_layers.get_l0_identity()
    assert "PT Tax Intelligence Layer" in identity


def test_l1_facts_basic(memory_layers):
    """Should return basic L1 facts."""
    facts = memory_layers.get_l1_facts()
    assert "Sistema: Análisis fiscal" in facts
    assert "CIVA" in facts


def test_l1_facts_with_recent(memory_layers):
    """Should include recent decisions."""
    facts = memory_layers.get_l1_facts(recent_decisions=[{"decision": "deductible"}])
    assert "Recientes: deductible" in facts


def test_l1_facts_with_project(memory_layers):
    """Should include active project."""
    facts = memory_layers.get_l1_facts(active_project="FCT")
    assert "Proyecto activo: FCT" in facts


def test_l2_room_context_known_pair(memory_layers):
    """Should return specific context for known entity/project."""
    context = memory_layers.get_l2_room_context("researcher", "FCT")
    assert "Investigador FCT" in context


def test_l2_room_context_unknown_pair(memory_layers):
    """Should return default context for unknown pair."""
    context = memory_layers.get_l2_room_context("unknown", "unknown")
    assert "Contexto padrão" in context


def test_l3_deep_search(memory_layers, mock_semantic):
    """Should perform semantic search."""
    results = memory_layers.get_l3_deep_search("test query", n_results=5)
    assert isinstance(results, list)
    mock_semantic.search.assert_called_once_with("test query", n_results=5)


def test_l3_deep_search_handles_error(memory_layers, mock_semantic):
    """Should return empty list on error."""
    mock_semantic.search.side_effect = Exception("Search failed")
    results = memory_layers.get_l3_deep_search("test")
    assert results == []


def test_save_to_memory(memory_layers, mock_semantic):
    """Should save decision to semantic memory."""
    memory_layers.save_to_memory(
        decision_id="123",
        description="Test expense",
        decision="deductible",
        explanation="Test explanation",
        legal_basis=[{"code": "CIVA", "article": "20º"}],
        metadata={"operation_type": "expense"},
    )
    mock_semantic.add_decision.assert_called_once()


def test_save_to_memory_handles_error(memory_layers, mock_semantic):
    """Should log warning if save fails."""
    mock_semantic.add_decision.side_effect = Exception("DB error")
    # Should not raise
    memory_layers.save_to_memory(
        decision_id="123",
        description="Test",
        decision="deductible",
        explanation="Test",
        legal_basis=[],
        metadata={},
    )


def test_build_context_l0(memory_layers):
    """Should build L0 context."""
    ctx = memory_layers.build_context(layer="L0")
    assert "PT Tax Intelligence Layer" in ctx


def test_build_context_l1(memory_layers):
    """Should build L1 context."""
    ctx = memory_layers.build_context(layer="L1")
    assert "CIVA" in ctx


def test_build_context_l2(memory_layers):
    """Should build L2 context."""
    ctx = memory_layers.build_context(layer="L2", entity_type="researcher", project_type="FCT")
    assert "Investigador FCT" in ctx


def test_build_context_l3(memory_layers, mock_semantic):
    """Should build L3 context with search results."""
    mock_semantic.search.return_value = [
        {"id": "abc123", "description": "Similar decision about expenses"},
        {"id": "def456", "description": "Another related case"},
    ]
    ctx = memory_layers.build_context(layer="L3", query="test")
    assert "Similar:" in ctx
    assert "expenses" in ctx or "case" in ctx
