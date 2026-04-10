import logging
from datetime import datetime
from typing import Optional
from app.models import TaxAnalysisInput, TaxAnalysisOutput, LegalCitation

logger = logging.getLogger(__name__)


class DecisionAggregator:
    """Aggregates results from Rule Engine and LLM."""
    
    DISCLAIMER = "This is a preliminary automated assessment. Validate with financial or legal services."
    
    async def decide(
        self,
        input_data: TaxAnalysisInput,
        rule_result: Optional[TaxAnalysisOutput],
        llm_result: Optional[TaxAnalysisOutput],
    ) -> TaxAnalysisOutput:
        """Combine results and produce final decision."""
        
        # Priority 1: Rule engine result (deterministic)
        if rule_result:
            final = rule_result.model_copy()
            final.explanation = f"{final.explanation}\n\n{self.DISCLAIMER}"
            final.assumptions.append(f"Context: {input_data.context.model_dump_json()}")
            return final
        
        # Priority 2: LLM result (with validation)
        if llm_result:
            # Check if LLM has sufficient legal basis
            if len(llm_result.legal_basis) < 2 and llm_result.confidence > 0.7:
                # Downgrade confidence if < 2 sources
                llm_result.confidence = min(llm_result.confidence, 0.6)
                llm_result.risks.append("Base legal insuficiente - apenas uma fonte")
            
            final = llm_result.model_copy()
            final.explanation = f"{final.explanation}\n\n{self.DISCLAIMER}"
            return final
        
        # No results - return uncertain
        return TaxAnalysisOutput(
            decision="uncertain",
            confidence=0.10,
            legal_basis=[],
            explanation=f"Não foi possível analisar esta operação.\n\n{self.DISCLAIMER}",
            risks=["Sistema indisponível"],
            assumptions=[input_data.model_dump_json()],
            required_followup=["Tentar novamente mais tarde"],
            risk_level="high",
            legal_version_timestamp=datetime.utcnow().isoformat() + "Z",
        )
    
    def calculate_confidence(
        self,
        rule_result: Optional[TaxAnalysisOutput],
        llm_result: Optional[TaxAnalysisOutput],
    ) -> float:
        """Calculate combined confidence score."""
        
        if rule_result:
            return max(rule_result.confidence, 0.8)
        
        if llm_result:
            return llm_result.confidence * 0.7
        
        return 0.1
    
    def assess_risks(
        self,
        rule_result: Optional[TaxAnalysisOutput],
        llm_result: Optional[TaxAnalysisOutput],
    ) -> list[str]:
        """Aggregate risks from all sources."""
        
        risks = []
        
        if rule_result:
            risks.extend(rule_result.risks)
        
        if llm_result:
            risks.extend(llm_result.risks)
        
        return list(set(risks)) if risks else []


_aggregator: Optional[DecisionAggregator] = None


def get_decision_aggregator() -> DecisionAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = DecisionAggregator()
    return _aggregator
