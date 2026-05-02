"""
Tests for graph router endpoints.

Tests: /tax/graph/stats, /tax/graph/gmif-summary, /tax/graph/by-gmif/{gmif_type}, /tax/graph/contradictions, /tax/graph/timeline/{entity}
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.routers.graph import (
    get_graph_stats,
    get_gmif_summary,
    get_decisions_by_gmif,
    get_contradictions,
    get_timeline,
)


class TestGraphEndpoints:
    """Test graph router endpoints."""

    @pytest.mark.asyncio
    async def test_get_graph_stats_returns_stats(self, mock_graph_builder):
        """Should return graph statistics."""
        response = await get_graph_stats()
        assert "total_nodes" in response
        assert "total_edges" in response
        assert "gmif_distribution" in response
        assert response["total_nodes"] == 100

    @pytest.mark.asyncio
    async def test_get_graph_stats_error_handling(self, mock_graph_builder):
        """Should raise HTTPException on error."""
        from fastapi import HTTPException

        mock_graph_builder.get_stats.side_effect = Exception("DB error")

        with pytest.raises(HTTPException) as exc_info:
            await get_graph_stats()
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_gmif_summary_returns_summary(self, mock_graph_builder):
        """Should return GMIF summary."""
        response = await get_gmif_summary()
        assert "total_nodes" in response
        assert response["total_nodes"] == 100

    @pytest.mark.asyncio
    async def test_get_decisions_by_gmif(self, mock_graph_builder):
        """Should return decisions filtered by GMIF type."""
        response = await get_decisions_by_gmif("M1", limit=10)
        assert "gmif_type" in response
        assert response["gmif_type"] == "M1"
        assert "decisions" in response

    @pytest.mark.asyncio
    async def test_get_decisions_by_gmif_limit(self, mock_graph_builder):
        """Should respect limit parameter."""
        await get_decisions_by_gmif("M2", limit=50)
        mock_graph_builder.get_decisions_by_gmif.assert_called_with("M2", limit=50)

    @pytest.mark.asyncio
    async def test_find_contradictions(self, mock_graph_builder):
        """Should return contradictions list."""
        response = await get_contradictions()
        assert "count" in response
        assert "contradictions" in response

    @pytest.mark.asyncio
    async def test_find_contradictions_for_decision(self, mock_graph_builder):
        """Should filter contradictions by decision_id."""
        await get_contradictions(decision_id="test-id-123")
        mock_graph_builder.find_contradictions.assert_called_once_with("test-id-123")

    @pytest.mark.asyncio
    async def test_get_timeline(self, mock_audit_repo, monkeypatch):
        """Should return timeline for entity."""
        now = datetime.now(timezone.utc)
        mock_decision = type('Decision', (), {
            'created_at': now - timedelta(days=1),
            'decision': 'deductible',
            'confidence': 0.9,
            'description': 'Test expense'
        })()
        mock_audit_repo.get_decisions.return_value = [mock_decision]

        monkeypatch.setattr(
            "app.routers.graph.get_audit_repository",
            lambda: mock_audit_repo
        )

        response = await get_timeline("researcher:internal")
        assert "entity" in response
        assert "timeline" in response
        assert len(response["timeline"]) == 1
