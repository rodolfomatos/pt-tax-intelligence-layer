"""
Tests for SemanticMemory.

Tests ChromaDB-based semantic memory for decisions.
"""

import pytest
from unittest.mock import MagicMock
from app.data.memory.semantic import SemanticMemory, get_semantic_memory


@pytest.fixture
def mock_chromadb(monkeypatch):
    """Mock chromadb client and collection."""
    mock_client = MagicMock()
    mock_collection = MagicMock()
    
    mock_client.get_or_create_collection.return_value = mock_collection
    monkeypatch.setattr("chromadb.PersistentClient", MagicMock(return_value=mock_client))
    
    return {
        "client": mock_client,
        "collection": mock_collection
    }


def test_semantic_memory_init_success(mock_chromadb):
    """Should initialize successfully with chromadb."""
    memory = SemanticMemory(persist_directory="/tmp/test")
    
    assert memory._enabled is True
    assert memory.client is not None
    assert memory.collection is not None
    mock_chromadb["client"].get_or_create_collection.assert_called_once()


def test_semantic_memory_init_failure(monkeypatch):
    """Should disable memory on initialization failure."""
    # Make chromadb.PersistentClient raise exception
    monkeypatch.setattr("chromadb.PersistentClient", MagicMock(side_effect=Exception("DB error")))
    
    memory = SemanticMemory(persist_directory="/tmp/test")
    
    assert memory._enabled is False
    assert memory.client is None
    assert memory.collection is None


def test_add_decision_when_enabled(mock_chromadb):
    """Should add decision to collection when enabled."""
    memory = SemanticMemory(persist_directory="/tmp/test")
    memory.add_decision(
        decision_id="test-dec-123",
        description="Test expense description",
        decision="deductible",
        explanation="Because it's business related",
        legal_basis=[{"code": "CIVA", "article": "20º", "excerpt": "test"}],
        metadata={"entity_type": "researcher", "project_type": "FCT"}
    )
    
    memory.collection.add.assert_called_once()
    call_args = memory.collection.add.call_args
    
    assert call_args[1]["ids"] == ["test-dec-123"]
    assert "Test expense description" in call_args[1]["documents"][0]
    assert call_args[1]["metadatas"][0]["decision"] == "deductible"


def test_add_decision_when_disabled(monkeypatch):
    """Should skip add when disabled."""
    # Force disabled
    monkeypatch.setattr("chromadb.PersistentClient", MagicMock(side_effect=Exception("error")))
    
    memory = SemanticMemory(persist_directory="/tmp/test")
    assert memory._enabled is False
    
    # Should not raise
    memory.add_decision(
        decision_id="test-dec-123",
        description="Test",
        decision="deductible",
        explanation="Explanation",
        legal_basis=[],
        metadata={}
    )
    
    assert memory.collection is None


def test_search_returns_results(mock_chromadb):
    """Should return search results from collection."""
    memory = SemanticMemory(persist_directory="/tmp/test")
    
    # Mock query response
    memory.collection.query.return_value = {
        "ids": [["result1", "result2"]],
        "documents": [["Doc 1", "Doc 2"]],
        "metadatas": [[{"decision": "deductible", "timestamp": "2025-01-15T10:30:00Z"}, {"decision": "non_deductible", "timestamp": "2025-01-14T09:00:00Z"}]],
        "distances": [[0.1, 0.2]]
    }
    
    results = memory.search("business expense", n_results=5)
    
    assert len(results) == 2
    assert results[0]["id"] == "result1"
    assert results[0]["description"] == "Doc 1"
    assert results[0]["decision"] == "deductible"
    assert results[0]["distance"] == 0.1
    assert results[1]["id"] == "result2"


def test_search_with_filter(mock_chromadb):
    """Should apply filter to query."""
    memory = SemanticMemory(persist_directory="/tmp/test")
    memory.collection.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]]
    }
    
    memory.search("test", n_results=5, filter_decision="deductible")
    
    call_args = memory.collection.query.call_args
    assert call_args[1]["where"] == {"decision": "deductible"}


def test_search_no_results(mock_chromadb):
    """Should return empty list when no results."""
    memory = SemanticMemory(persist_directory="/tmp/test")
    memory.collection.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]]
    }
    
    results = memory.search("nonexistent")
    
    assert results == []


def test_search_when_disabled(monkeypatch):
    """Should return empty list when disabled."""
    monkeypatch.setattr("chromadb.PersistentClient", MagicMock(side_effect=Exception("error")))
    
    memory = SemanticMemory(persist_directory="/tmp/test")
    assert memory._enabled is False
    
    results = memory.search("test")
    assert results == []


def test_delete_when_enabled(mock_chromadb):
    """Should delete decision from collection."""
    memory = SemanticMemory(persist_directory="/tmp/test")
    
    memory.delete("test-dec-123")
    
    memory.collection.delete.assert_called_once_with(ids=["test-dec-123"])


def test_delete_when_disabled(monkeypatch):
    """Should skip delete when disabled."""
    monkeypatch.setattr("chromadb.PersistentClient", MagicMock(side_effect=Exception("error")))
    
    memory = SemanticMemory(persist_directory="/tmp/test")
    memory.delete("test-dec-123")
    
    # collection is None, so no delete call
    assert memory.collection is None


def test_count_when_enabled(mock_chromadb):
    """Should return count from collection."""
    memory = SemanticMemory(persist_directory="/tmp/test")
    memory.collection.count.return_value = 42
    
    count = memory.count()
    
    assert count == 42
    memory.collection.count.assert_called_once()


def test_count_when_disabled(monkeypatch):
    """Should return 0 when disabled."""
    monkeypatch.setattr("chromadb.PersistentClient", MagicMock(side_effect=Exception("error")))
    
    memory = SemanticMemory(persist_directory="/tmp/test")
    count = memory.count()
    
    assert count == 0


def test_get_semantic_memory_singleton():
    """Should return singleton instance."""
    # Reset global for test
    import app.data.memory.semantic as semantic_module
    semantic_module._memory = None
    
    mem1 = get_semantic_memory()
    mem2 = get_semantic_memory()
    
    assert mem1 is mem2
    # Cleanup
    semantic_module._memory = None
