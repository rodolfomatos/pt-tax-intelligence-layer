"""
Tests for LLMReasoning service.

Tests the reasoning layer that uses LLMs with grounding.
"""

import pytest
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
