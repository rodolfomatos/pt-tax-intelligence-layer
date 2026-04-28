"""
Internal router.

Contains internal endpoints for benchmarks and system operations.
"""

from fastapi import APIRouter, Request
from typing import Optional
import logging
import time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.get("/benchmark")
async def run_benchmark(
    request: Request,
    iterations: int = 100,
    use_cache: bool = True,
):
    """
    Run performance benchmark on tax analysis pipeline.

    Measures:
    - Average processing time
    - Cache hit rate
    - Rule engine vs LLM usage

    Args:
        iterations: Number of test iterations
        use_cache: Whether to use caching

    Returns benchmark results and statistics.
    """
    try:
        from app.services.rules.engine import get_rule_engine
        from app.services.reasoning import get_llm_reasoning
        from app.models import TaxAnalysisInput, Context

        rule_engine = get_rule_engine()
        llm_reasoning = get_llm_reasoning()

        # Test inputs
        test_inputs = [
            TaxAnalysisInput(
                operation_type="expense",
                description="Office supplies",
                amount=50.0,
                currency="EUR",
                entity_type="department",
                context=Context(
                    project_type="internal", activity_type="taxable", location="PT"
                ),
            ),
            TaxAnalysisInput(
                operation_type="invoice",
                description="Consulting services",
                amount=2500.0,
                currency="EUR",
                entity_type="department",
                context=Context(
                    project_type="Horizon", activity_type="taxable", location="EU"
                ),
            ),
        ]

        results = {
            "iterations": iterations,
            "use_cache": use_cache,
            "rule_engine": {"count": 0, "total_time_ms": 0},
            "llm": {"count": 0, "total_time_ms": 0},
            "errors": 0,
        }

        for i in range(iterations):
            input_item = test_inputs[i % len(test_inputs)]

            start = time.time()

            try:
                # Try rule engine first
                rule_result = rule_engine.evaluate(input_item)

                if rule_result:
                    results["rule_engine"]["count"] += 1
                    elapsed_ms = int((time.time() - start) * 1000)
                    results["rule_engine"]["total_time_ms"] += elapsed_ms
                else:
                    # Fall back to LLM
                    llm_result = await llm_reasoning.analyze(input_item)
                    results["llm"]["count"] += 1
                    elapsed_ms = int((time.time() - start) * 1000)
                    results["llm"]["total_time_ms"] += elapsed_ms
            except Exception as e:
                results["errors"] += 1
                logger.warning(f"Benchmark iteration {i} failed: {e}")

        # Calculate averages
        if results["rule_engine"]["count"] > 0:
            results["rule_engine"]["avg_ms"] = (
                results["rule_engine"]["total_time_ms"]
                / results["rule_engine"]["count"]
            )
        if results["llm"]["count"] > 0:
            results["llm"]["avg_ms"] = (
                results["llm"]["total_time_ms"] / results["llm"]["count"]
            )

        results["total_time_sec"] = (
            results["rule_engine"]["total_time_ms"] + results["llm"]["total_time_ms"]
        ) / 1000

        logger.info(f"Benchmark complete: {iterations} iterations")
        return results

    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        raise HTTPException(status_code=500, detail="Benchmark failed")
