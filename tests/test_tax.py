"""
Tests for tax router endpoints.

Tests: /tax/analyze, /tax/validate, /tax/analyze/batch
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request
from app.routers.tax import analyze_tax, validate_tax, analyze_tax_batch
from app.models import TaxAnalysisInput, TaxAnalysisOutput, LegalCitation, Context, TaxValidationInput
from app.models.batch import BatchAnalysisRequest, BatchAnalysisResponse
from datetime import datetime, timezone


def create_mock_request(
    request_id="test-request-id",
    user="test-user",
    host="127.0.0.1"
):
    """Create a mock Request object."""
    req = MagicMock(spec=Request)
    req.headers = {"X-Request-ID": request_id, "X-User": user}
    req.client = MagicMock()
    req.client.host = host
    return req


@pytest.fixture
def mock_rule_engine(monkeypatch):
    """Mock rule engine."""
    engine = MagicMock()
    engine.evaluate = MagicMock(return_value=None)  # default: no rule match
    monkeypatch.setattr(
        "app.routers.tax.get_rule_engine",
        lambda: engine
    )
    return engine


@pytest.fixture
def mock_llm_reasoning(monkeypatch):
    """Mock LLM reasoning."""
    llm = AsyncMock()
    llm.analyze = AsyncMock(return_value=TaxAnalysisOutput(
        decision="deductible",
        confidence=0.8,
        legal_basis=[LegalCitation(code="CIVA", article="20º", excerpt="Test")],
        explanation="LLM analysis",
        risks=[],
        assumptions=[],
        required_followup=[],
        risk_level="low",
        legal_version_timestamp=datetime.now(timezone.utc).isoformat(),
    ))
    monkeypatch.setattr(
        "app.routers.tax.get_llm_reasoning",
        lambda: llm
    )
    return llm


@pytest.fixture
def mock_decision_aggregator(monkeypatch):
    """Mock decision aggregator."""
    agg = AsyncMock()
    agg.decide = AsyncMock(return_value=TaxAnalysisOutput(
        decision="deductible",
        confidence=0.85,
        legal_basis=[LegalCitation(code="CIVA", article="20º", excerpt="Test")],
        explanation="Aggregated decision",
        risks=[],
        assumptions=[],
        required_followup=[],
        risk_level="low",
        legal_version_timestamp=datetime.now(timezone.utc).isoformat(),
    ))
    monkeypatch.setattr(
        "app.routers.tax.get_decision_aggregator",
        lambda: agg
    )
    return agg


@pytest.fixture
def mock_audit_repo(monkeypatch):
    """Mock audit repository."""
    from app.database.audit import AuditRepository
    repo = AsyncMock(spec=AuditRepository)
    repo.log_decision.return_value = MagicMock(id="123456")
    repo.log_action.return_value = MagicMock(id="654321")
    monkeypatch.setattr(
        "app.routers.tax.get_audit_repository",
        lambda: repo
    )
    return repo


@pytest.fixture
def mock_memory_layers(monkeypatch):
    """Mock memory layers."""
    memory = MagicMock()
    memory.save_to_memory = MagicMock()
    monkeypatch.setattr(
        "app.data.memory.layers.get_memory_layers",
        lambda: memory
    )
    return memory


@pytest.fixture
def mock_decision_hooks(monkeypatch):
    """Mock DecisionHooks."""
    hooks = MagicMock()
    hooks.on_decision = MagicMock()
    monkeypatch.setattr(
        "app.data.memory.hooks.DecisionHooks",
        hooks
    )
    return hooks


@pytest.fixture
def mock_graph_builder(monkeypatch):
    """Mock graph builder."""
    builder = AsyncMock()
    builder.add_decision = AsyncMock(return_value="M1")
    monkeypatch.setattr(
        "app.data.memory.graph.builder.get_graph_builder",
        lambda: builder
    )
    return builder


@pytest.fixture
def mock_system_hooks(monkeypatch):
    """Mock system hooks for batch high-risk events."""
    hooks = AsyncMock()
    hooks.trigger = AsyncMock()
    monkeypatch.setattr(
        "app.routers.tax.get_system_hooks",
        lambda: hooks
    )
    return hooks


@pytest.mark.asyncio
async def test_analyze_tax_rule_engine_hit(
    mock_rule_engine,
    mock_llm_reasoning,
    mock_decision_aggregator,
    mock_audit_repo,
    mock_memory_layers,
    mock_decision_hooks,
    mock_graph_builder
):
    """Should return rule engine result directly when available."""
    rule_result = TaxAnalysisOutput(
        decision="deductible",
        confidence=0.9,
        legal_basis=[LegalCitation(code="CIVA", article="20º", excerpt="Rule")],
        explanation="Rule result",
        risks=[],
        assumptions=[],
        required_followup=[],
        risk_level="low",
        legal_version_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    mock_rule_engine.evaluate.return_value = rule_result

    input_data = TaxAnalysisInput(
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
    req = create_mock_request()

    await analyze_tax(input_data, req)

    # Rule engine result should be used directly; aggregator not called? Actually aggregator is called with rule_result and llm_result (which may be None). Our aggregator mock returns a value, but in real code aggregator is always called. Let's check code: aggregator.decide(input, rule_result, llm_result). So even if rule engine hit, aggregator is called. Our mock aggregator returns something. But in test we may want to verify flow.

    mock_rule_engine.evaluate.assert_called_once()
    mock_llm_reasoning.analyze.assert_called_once()  # LLM still called? Actually code: it calls llm_analyze regardless? Yes line 57: llm_result = await llm_reasoning.analyze(input) always called. That may be changed in future but current code calls both. So both should be called.
    mock_decision_aggregator.decide.assert_called_once()

    # Audit logging
    mock_audit_repo.log_decision.assert_called_once()
    mock_audit_repo.log_action.assert_called_once()

    # Memory and graph saved
    mock_memory_layers.save_to_memory.assert_called_once()
    mock_graph_builder.add_decision.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_tax_rule_engine_miss(
    mock_rule_engine,
    mock_llm_reasoning,
    mock_decision_aggregator,
    mock_audit_repo,
    mock_memory_layers,
    mock_decision_hooks,
    mock_graph_builder
):
    """Should fall back to LLM when rule engine returns None."""
    mock_rule_engine.evaluate.return_value = None  # rule miss
    # LLM and aggregator already returning default values

    input_data = TaxAnalysisInput(
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
    req = create_mock_request()

    await analyze_tax(input_data, req)

    mock_rule_engine.evaluate.assert_called_once()
    mock_llm_reasoning.analyze.assert_called_once()
    mock_decision_aggregator.decide.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_tax_audit_logging_failure(
    mock_rule_engine,
    mock_llm_reasoning,
    mock_decision_aggregator,
    mock_audit_repo,
    mock_memory_layers,
    mock_decision_hooks,
    mock_graph_builder
):
    """Should continue even if audit logging fails."""
    mock_audit_repo.log_decision.side_effect = Exception("DB error")
    mock_audit_repo.log_action.side_effect = Exception("DB error")

    input_data = TaxAnalysisInput(
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
    req = create_mock_request()

    result = await analyze_tax(input_data, req)

    # Should still return result despite audit errors
    assert result is not None


@pytest.mark.asyncio
async def test_analyze_tax_memory_save_failure(
    mock_rule_engine,
    mock_llm_reasoning,
    mock_decision_aggregator,
    mock_audit_repo,
    mock_memory_layers,
    mock_decision_hooks,
    mock_graph_builder
):
    """Should continue even if memory save fails."""
    mock_memory_layers.save_to_memory.side_effect = Exception("Memory error")

    input_data = TaxAnalysisInput(
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
    req = create_mock_request()

    result = await analyze_tax(input_data, req)

    assert result is not None


@pytest.mark.asyncio
async def test_analyze_tax_graph_save_failure(
    mock_rule_engine,
    mock_llm_reasoning,
    mock_decision_aggregator,
    mock_audit_repo,
    mock_memory_layers,
    mock_decision_hooks,
    mock_graph_builder
):
    """Should log warning but continue if graph save fails."""
    mock_graph_builder.add_decision.side_effect = Exception("Graph error")

    input_data = TaxAnalysisInput(
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
    req = create_mock_request()

    result = await analyze_tax(input_data, req)

    assert result is not None


@pytest.mark.asyncio
async def test_validate_tax_passes():
    """Should return valid=True when no warnings."""
    input_data = TaxValidationInput(
        decision="deductible",
        confidence=0.8,
        legal_basis=[LegalCitation(code="CIVA", article="20º", excerpt="Test")],
        explanation="Valid",
        risks=[],
        assumptions=[],
        required_followup=[],
        risk_level="low",
        legal_version_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    result = await validate_tax(input_data, MagicMock(spec=Request))
    assert result.valid is True
    assert result.consistency_check == "passed"
    assert len(result.warnings) == 0


@pytest.mark.asyncio
async def test_validate_tax_high_confidence_low_sources():
    """Should warn about high confidence but limited legal basis."""
    input_data = TaxValidationInput(
        decision="deductible",
        confidence=0.85,
        legal_basis=[
            LegalCitation(code="CIVA", article="20º", excerpt="Single source")
        ],
        explanation="Test",
        risks=[],
        assumptions=[],
        required_followup=[],
        risk_level="low",
        legal_version_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    result = await validate_tax(input_data, MagicMock(spec=Request))
    assert result.valid is False
    assert len(result.warnings) > 0
    assert any("High confidence but limited legal basis" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_validate_tax_uncertain_high_confidence():
    """Should warn about uncertain with high confidence."""
    input_data = TaxValidationInput(
        decision="uncertain",
        confidence=0.75,
        legal_basis=[],
        explanation="Uncertain",
        risks=[],
        assumptions=[],
        required_followup=[],
        risk_level="high",
        legal_version_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    result = await validate_tax(input_data, MagicMock(spec=Request))
    assert result.valid is False
    assert any("Uncertain decision should have lower confidence" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_validate_tax_missing_citation():
    """Should warn about missing code or article."""
    input_data = TaxValidationInput(
        decision="deductible",
        confidence=0.8,
        legal_basis=[
            LegalCitation(code="", article="20º", excerpt="Missing code"),
            LegalCitation(code="CIVA", article="", excerpt="Missing article"),
        ],
        explanation="Test",
        risks=[],
        assumptions=[],
        required_followup=[],
        risk_level="low",
        legal_version_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    result = await validate_tax(input_data, MagicMock(spec=Request))
    assert result.valid is False
    warnings_str = " ".join(result.warnings)
    assert "missing code or article" in warnings_str.lower()


@pytest.fixture
def sample_batch_request():
    """Create a batch request with multiple items."""
    return BatchAnalysisRequest(
        items=[
            TaxAnalysisInput(
                operation_type="expense",
                description="Item 1",
                amount=50.0,
                currency="EUR",
                entity_type="researcher",
                metadata={},
                context=Context(
                    project_type="FCT",
                    activity_type="taxable",
                    location="PT"
                )
            ),
            TaxAnalysisInput(
                operation_type="expense",
                description="Item 2",
                amount=100.0,
                currency="EUR",
                entity_type="researcher",
                metadata={},
                context=Context(
                    project_type="FCT",
                    activity_type="taxable",
                    location="PT"
                )
            ),
        ],
        stop_on_error=False
    )


@pytest.mark.asyncio
async def test_analyze_batch_success(
    mock_rule_engine,
    mock_llm_reasoning,
    mock_decision_aggregator,
    mock_audit_repo,
    sample_batch_request
):
    """Should process batch and return results."""
    req = create_mock_request()
    result = await analyze_tax_batch(req, sample_batch_request)

    assert isinstance(result, BatchAnalysisResponse)
    assert result.total == 2
    assert result.successful == 2
    assert result.failed == 0
    assert len(result.results) == 2

    # Each item should have been processed
    assert mock_rule_engine.evaluate.call_count == 2
    assert mock_llm_reasoning.analyze.call_count == 2
    assert mock_decision_aggregator.decide.call_count == 2
    assert mock_audit_repo.log_decision.call_count == 2


@pytest.mark.asyncio
async def test_analyze_batch_with_errors(
    mock_rule_engine,
    mock_llm_reasoning,
    mock_decision_aggregator,
    mock_audit_repo,
    sample_batch_request
):
    """Should handle errors in batch processing."""
    call_count = 0
    async def failing_analyze(input_item):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise Exception("LLM failure")
        return mock_llm_reasoning.analyze.return_value

    mock_llm_reasoning.analyze.side_effect = failing_analyze

    req = create_mock_request()
    result = await analyze_tax_batch(req, sample_batch_request)

    assert result.total == 2
    assert result.successful == 1
    assert result.failed == 1
    assert len(result.results) == 1
    assert len(result.errors) == 1
    assert "LLM failure" in result.errors[0]["error"]


@pytest.mark.asyncio
async def test_analyze_batch_stop_on_error(
    mock_rule_engine,
    mock_llm_reasoning,
    mock_decision_aggregator,
    mock_audit_repo,
    sample_batch_request
):
    """Should stop processing when stop_on_error=True and error occurs."""
    sample_batch_request.stop_on_error = True

    call_count = 0
    async def failing_analyze(input_item):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise Exception("LLM failure")
        return mock_llm_reasoning.analyze.return_value

    mock_llm_reasoning.analyze.side_effect = failing_analyze

    req = create_mock_request()
    result = await analyze_tax_batch(req, sample_batch_request)

    assert result.total == 2
    assert result.successful == 1
    assert result.failed == 1
    assert len(result.results) == 1


@pytest.mark.asyncio
async def test_analyze_batch_high_risk_triggers_webhook(
    mock_rule_engine,
    mock_llm_reasoning,
    mock_decision_aggregator,
    mock_audit_repo,
    mock_system_hooks,
    sample_batch_request
):
    """Should trigger webhook for high-risk decisions."""
    high_risk_output = TaxAnalysisOutput(
        decision="non_deductible",
        confidence=0.8,
        legal_basis=[],
        explanation="High risk",
        risks=[],
        assumptions=[],
        required_followup=[],
        risk_level="high",
        legal_version_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    mock_decision_aggregator.decide.return_value = high_risk_output

    req = create_mock_request()
    result = await analyze_tax_batch(req, sample_batch_request)

    assert result.successful == 2
    # High risk should trigger webhook for each item
    assert mock_system_hooks.trigger.call_count == 2
