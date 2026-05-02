"""
Tests for DecisionAggregator service.

Tests the aggregation of rule engine and LLM results.
"""

import pytest
from datetime import datetime, timezone
from app.services.decision import DecisionAggregator
from app.models import TaxAnalysisInput, TaxAnalysisOutput, LegalCitation, Context


@pytest.fixture
def aggregator():
    """Create a DecisionAggregator."""
    return DecisionAggregator()


@pytest.fixture
def base_input():
    """Create a base TaxAnalysisInput for tests."""
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
def rule_output():
    """Create a rule engine output."""
    return TaxAnalysisOutput(
        decision="deductible",
        confidence=0.9,
        legal_basis=[
            LegalCitation(code="CIVA", article="20º", excerpt="Test excerpt")
        ],
        explanation="Rule engine decision",
        risks=[],
        assumptions=[],
        required_followup=[],
        risk_level="low",
        legal_version_timestamp=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def llm_output():
    """Create an LLM output."""
    return TaxAnalysisOutput(
        decision="partially_deductible",
        confidence=0.8,
        legal_basis=[
            LegalCitation(code="CIRC", article="15º", excerpt="Another excerpt")
        ],
        explanation="LLM decision",
        risks=["risk1"],
        assumptions=["assumption1"],
        required_followup=["followup1"],
        risk_level="medium",
        legal_version_timestamp=datetime.now(timezone.utc).isoformat(),
    )


@pytest.mark.asyncio
async def test_decide_with_rule_result(aggregator, base_input, rule_output):
    """Should return rule result with appended disclaimer."""
    result = await aggregator.decide(base_input, rule_output, None)
    assert result.decision == rule_output.decision
    assert result.confidence == rule_output.confidence
    assert aggregator.DISCLAIMER in result.explanation
    assert f"Context: {base_input.context.model_dump_json()}" in result.assumptions


@pytest.mark.asyncio
async def test_decide_with_llm_result_when_rule_missing(aggregator, base_input, llm_output):
    """Should return LLM result with disclaimer."""
    result = await aggregator.decide(base_input, None, llm_output)
    assert result.decision == llm_output.decision
    assert aggregator.DISCLAIMER in result.explanation


@pytest.mark.asyncio
async def test_decide_with_llm_confidence_downgrade(aggregator, base_input):
    """Should downgrade confidence if legal basis < 2 and confidence > 0.7."""
    llm_output = TaxAnalysisOutput(
        decision="deductible",
        confidence=0.8,
        legal_basis=[
            LegalCitation(code="CIVA", article="20º", excerpt="Only one source")
        ],
        explanation="Test",
        risks=[],
        assumptions=[],
        required_followup=[],
        risk_level="low",
        legal_version_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    result = await aggregator.decide(base_input, None, llm_output)
    assert result.confidence <= 0.6
    assert "Base legal insuficiente - apenas uma fonte" in result.risks


@pytest.mark.asyncio
async def test_decide_when_no_results(aggregator, base_input):
    """Should return uncertain when both sources missing."""
    result = await aggregator.decide(base_input, None, None)
    assert result.decision == "uncertain"
    assert result.confidence == 0.10
    assert aggregator.DISCLAIMER in result.explanation
    assert "Sistema indisponível" in result.risks
    assert "Tentar novamente mais tarde" in result.required_followup


def test_calculate_confidence_with_rule(aggregator, rule_output):
    """Should return max(rule.confidence, 0.8) when rule result present."""
    confidence = aggregator.calculate_confidence(rule_output, None)
    assert confidence == max(rule_output.confidence, 0.8)


def test_calculate_confidence_with_llm(aggregator, llm_output):
    """Should return llm.confidence * 0.7 when rule missing."""
    confidence = aggregator.calculate_confidence(None, llm_output)
    assert confidence == pytest.approx(llm_output.confidence * 0.7)


def test_calculate_confidence_no_results(aggregator):
    """Should return 0.1 when no results."""
    confidence = aggregator.calculate_confidence(None, None)
    assert confidence == 0.1


def test_assess_risks_aggregates_both(aggregator, rule_output, llm_output):
    """Should aggregate risks from both sources."""
    risks = aggregator.assess_risks(rule_output, llm_output)
    # rule_output risks empty, llm risks ["risk1"]
    assert "risk1" in risks
    # Should be unique
    assert len(risks) == 1


def test_assess_risks_deduplication(aggregator):
    """Should deduplicate overlapping risks."""
    rule = TaxAnalysisOutput(
        decision="deductible", confidence=0.9, legal_basis=[], explanation="", risks=["common"], assumptions=[], required_followup=[], risk_level="low", legal_version_timestamp=datetime.now(timezone.utc).isoformat()
    )
    llm = TaxAnalysisOutput(
        decision="deductible", confidence=0.8, legal_basis=[], explanation="", risks=["common"], assumptions=[], required_followup=[], risk_level="low", legal_version_timestamp=datetime.now(timezone.utc).isoformat()
    )
    risks = aggregator.assess_risks(rule, llm)
    assert len(risks) == 1
    assert "common" in risks


def test_assess_risks_empty(aggregator):
    """Should return empty list when no risks."""
    rule = TaxAnalysisOutput(
        decision="deductible", confidence=0.9, legal_basis=[], explanation="", risks=[], assumptions=[], required_followup=[], risk_level="low", legal_version_timestamp=datetime.now(timezone.utc).isoformat()
    )
    llm = TaxAnalysisOutput(
        decision="deductible", confidence=0.8, legal_basis=[], explanation="", risks=[], assumptions=[], required_followup=[], risk_level="low", legal_version_timestamp=datetime.now(timezone.utc).isoformat()
    )
    risks = aggregator.assess_risks(rule, llm)
    assert risks == []
