"""
Tests for internal router endpoints.

Tests: /internal/benchmark
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request
from app.routers.internal import run_benchmark


@pytest.fixture
def mock_request():
    """Create a mock Request object."""
    return MagicMock(spec=Request)


@pytest.fixture
def mock_rule_engine(monkeypatch):
    """Mock the rule engine."""
    engine = MagicMock()
    engine.evaluate = MagicMock(return_value=True)  # default: rule engine hits
    monkeypatch.setattr(
        "app.services.rules.engine.get_rule_engine",
        lambda: engine
    )
    return engine


@pytest.fixture
def mock_llm(monkeypatch):
    """Mock the LLM reasoning service."""
    llm = AsyncMock()
    llm.analyze = AsyncMock(return_value=MagicMock(
        decision="deductible",
        confidence=0.8,
        legal_basis=[],
        explanation="LLM analysis",
        risks=[],
        assumptions=[],
        required_followup=[],
        risk_level="low",
        legal_version_timestamp="2024-01-01T00:00:00Z",
    ))
    monkeypatch.setattr(
        "app.services.reasoning.get_llm_reasoning",
        lambda: llm
    )
    return llm


@pytest.mark.asyncio
async def test_run_benchmark_basic(mock_request, mock_rule_engine, mock_llm):
    """Should run benchmark and return statistics."""
    # Configure rule engine to return True, False, True over 3 iterations
    mock_rule_engine.evaluate.side_effect = [True, False, True]
    result = await run_benchmark(mock_request, iterations=3, use_cache=True)

    assert result["iterations"] == 3
    assert "rule_engine" in result
    assert "llm" in result
    assert result["rule_engine"]["count"] == 2  # two rule hits
    assert result["llm"]["count"] == 1         # one fallback
    assert "total_time_sec" in result
    assert result["errors"] == 0


@pytest.mark.asyncio
async def test_run_benchmark_rule_engine_exception(mock_request, mock_rule_engine, mock_llm):
    """Should count errors when rule engine raises."""
    mock_rule_engine.evaluate.side_effect = Exception("Engine failure")
    result = await run_benchmark(mock_request, iterations=1)
    assert result["errors"] == 1


@pytest.mark.asyncio
async def test_run_benchmark_llm_exception(mock_request, mock_rule_engine, mock_llm):
    """Should count errors when LLM analyze raises."""
    mock_rule_engine.evaluate.side_effect = [False]  # force LLM fallback
    mock_llm.analyze.side_effect = Exception("LLM failure")
    result = await run_benchmark(mock_request, iterations=1)
    assert result["errors"] == 1


@pytest.mark.asyncio
async def test_run_benchmark_multiple_cycles(mock_request, mock_rule_engine, mock_llm):
    """Should correctly iterate over the two test inputs."""
    mock_rule_engine.evaluate.side_effect = [True, False, True, False]
    result = await run_benchmark(mock_request, iterations=4)
    assert mock_rule_engine.evaluate.call_count == 4
    # With 4 iterations, pattern: input0, input1, input0, input1
    # rule engine hits for input0 (even iterations), misses for input1 (odd)
    assert result["rule_engine"]["count"] == 2
    assert result["llm"]["count"] == 2
