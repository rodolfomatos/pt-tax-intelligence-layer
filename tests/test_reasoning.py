"""
Tests for LLMReasoning service.

Tests the reasoning layer that uses LLMs with grounding.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.reasoning import LLMReasoning, get_llm_reasoning
from app.models import TaxAnalysisInput, Context


@pytest.fixture
def sample_input():
    """Create a sample tax analysis input."""
    return TaxAnalysisInput(
        operation_type="expense",
        description="Alojamento em conferência",
        amount=150.0,
        currency="EUR",
        entity_type="researcher",
        context=Context(
            project_type="FCT",
            activity_type="taxable",
            location="PT",
        ),
    )


class TestLLMReasoning:
    """Test LLM reasoning service."""

    def test_singleton(self):
        """Should return singleton instance."""
        r1 = get_llm_reasoning()
        r2 = get_llm_reasoning()
        assert r1 is r2

    def test_build_user_prompt(self, sample_input):
        """Should build user prompt correctly."""
        reasoning = LLMReasoning()
        prompt = reasoning._build_user_prompt(sample_input)
        assert "Alojamento em conferência" in prompt
        assert "expense" in prompt
        assert "150" in prompt

    def test_build_legal_context(self, sample_input):
        """Should build legal context from search results."""
        reasoning = LLMReasoning()
        results = [
            {"code": "CIVA", "article": "20º", "excerpt": "Deduções..."},
            {"code": "CIRC", "article": "23º", "excerpt": "Custos..."},
        ]
        context = reasoning._build_legal_context(results)
        assert "CIVA" in context
        assert "CIRC" in context

    def test_parse_llm_response_valid_json(self):
        """Should parse valid JSON response."""
        reasoning = LLMReasoning()
        response = '''
        {
            "decision": "deductible",
            "confidence": 0.85,
            "legal_basis": [{"code": "CIVA", "article": "20º", "excerpt": "test"}],
            "explanation": "Test explanation",
            "risks": [],
            "assumptions": [],
            "required_followup": [],
            "risk_level": "low",
            "legal_version_timestamp": "2024-01-01T00:00:00Z"
        }
        '''
        result = reasoning._parse_llm_response(response)
        assert result is not None
        assert result.decision == "deductible"
        assert result.confidence == 0.85

    def test_parse_llm_response_malformed(self):
        """Should return None for malformed response."""
        reasoning = LLMReasoning()
        result = reasoning._parse_llm_response("Not JSON")
        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_fallback_path(self, monkeypatch, sample_input):
        """Should execute fallback analysis when IAEDU disabled."""
        # Mock ptdata client as async get_ptdata_client()
        mock_ptdata = AsyncMock()
        mock_ptdata.search_legislation = AsyncMock(return_value=[
            {"code": "CIVA", "article": "20º", "excerpt": "Deduções permitidas..."},
            {"code": "CIRC", "article": "23º", "excerpt": "Custos dedutíveis..."},
        ])
        mock_get_ptdata_client = AsyncMock(return_value=mock_ptdata)
        monkeypatch.setattr("app.services.reasoning.get_ptdata_client", mock_get_ptdata_client)

        # Mock memory layers
        mock_memory = MagicMock()
        mock_memory.build_context.return_value = "Memory context from L0/L1"
        mock_memory.get_l3_deep_search.return_value = []  # no similar decisions
        monkeypatch.setattr("app.services.reasoning.get_memory_layers", lambda: mock_memory)

        # Ensure use_iaedu is False
        from app.config import get_settings
        settings = get_settings()
        monkeypatch.setattr(settings, "use_iaedu", False)

        # Create reasoning (will use patched get_memory_layers)
        reasoning = LLMReasoning()
        result = await reasoning.analyze(sample_input)

        # Should return uncertain from fallback
        assert result.decision == "uncertain"
        assert result.confidence == 0.40
        # Should have called ptdata search
        mock_ptdata.search_legislation.assert_called_once()
        # Legal basis should contain citations from legislation results (up to 3)
        assert len(result.legal_basis) == 2
        assert result.legal_basis[0].code == "CIVA"
        assert result.risk_level == "medium"

    @pytest.mark.asyncio
    async def test_analyze_uses_iaedu_when_enabled(self, monkeypatch, sample_input):
        """Should use IAEDU when enabled and API key present."""
        # Mock ptdata as async get_ptdata_client()
        mock_ptdata = AsyncMock()
        mock_ptdata.search_legislation = AsyncMock(return_value=[
            {"code": "CIVA", "article": "20º", "excerpt": "Deduções..."}
        ])
        mock_get_ptdata_client = AsyncMock(return_value=mock_ptdata)
        monkeypatch.setattr("app.services.reasoning.get_ptdata_client", mock_get_ptdata_client)

        # Mock memory
        mock_memory = MagicMock()
        mock_memory.build_context.return_value = "Memory context"
        mock_memory.get_l3_deep_search.return_value = []
        monkeypatch.setattr("app.services.reasoning.get_memory_layers", lambda: mock_memory)

        # Mock IAEDU client (get_iaedu_client is sync)
        mock_iaedu = MagicMock()
        mock_iaedu.chat_complete = AsyncMock(return_value='{"decision":"deductible","confidence":0.9,"legal_basis":[],"explanation":"IAEDU analysis","risks":[],"assumptions":[],"required_followup":[],"risk_level":"low","legal_version_timestamp":"2024-01-01T00:00:00Z"}')
        monkeypatch.setattr("app.services.reasoning.get_iaedu_client", lambda: mock_iaedu)

        # Enable use_iaedu and set API key
        from app.config import get_settings
        settings = get_settings()
        monkeypatch.setattr(settings, "use_iaedu", True)
        monkeypatch.setattr(settings, "iaedu_api_key", "test-key")

        reasoning = LLMReasoning()
        result = await reasoning.analyze(sample_input)

        assert result.decision == "deductible"
        assert result.confidence == 0.9
        mock_iaedu.chat_complete.assert_called_once()

