import json
import logging
import re
from typing import Optional
from app.config import get_settings
from app.models import TaxAnalysisInput, TaxAnalysisOutput, LegalCitation
from app.data.ptdata.client import get_ptdata_client
from app.data.iaedu.client import get_iaedu_client
from app.data.memory.layers import get_memory_layers

logger = logging.getLogger(__name__)
settings = get_settings()


LLM_SYSTEM_PROMPT = """You are a tax analysis assistant specialized in Portuguese tax law for university administrative workflows.

IMPORTANT RULES:
1. ONLY answer if you can cite specific legal articles from the provided legislation
2. If no clear legal basis is found, return "uncertain" with confidence below 0.5
3. NEVER hallucinate legal articles or provisions
4. Use the retrieved legislation to support your answer
5. Portuguese tax codes: CIVA (IVA/VAT), CIRC (IRC/Corporate Tax), CIRS (IRS/Personal Tax)

Your response MUST be in Portuguese and follow this JSON format exactly:
{
  "decision": "deductible" | "non_deductible" | "partially_deductible" | "uncertain",
  "confidence": 0.0-1.0,
  "legal_basis": [{"code": "CIVA|CIRC|CIRS", "article": "Artigo Xº", "excerpt": "..."}],
  "explanation": "explanation in Portuguese",
  "risks": ["risk1", "risk2"],
  "assumptions": ["assumption1"],
  "required_followup": ["question1"],
  "risk_level": "low" | "medium" | "high"
}

Always include the disclaimer: "Esta é uma avaliação automática preliminar. Valide com os serviços financeiros ou jurídicos."

CONTEXT FROM MEMORY (use to inform your decision):
{memory_context}
"""


class LLMReasoning:
    """LLM-based reasoning layer using IAEDU or OpenAI/Ollama."""
    
    def __init__(self):
        self.use_iaedu = settings.use_iaedu
        self.model = settings.llm_model
        self.memory_layers = get_memory_layers()
    
    async def analyze(
        self,
        input_data: TaxAnalysisInput,
    ) -> Optional[TaxAnalysisOutput]:
        """Use LLM to analyze tax operation."""
        
        # Get memory context (L0 + L1)
        memory_context = self.memory_layers.build_context(
            layer="L1",
            entity_type=input_data.entity_type,
            project_type=input_data.context.project_type,
        )
        
        # Search for similar past decisions (L3 deep search)
        similar_decisions = self.memory_layers.get_l3_deep_search(
            query=input_data.description,
            n_results=3,
        )
        
        if similar_decisions:
            logger.info(f"Found {len(similar_decisions)} similar decisions")
        
        # Search legislation
        ptdata = await get_ptdata_client()
        
        try:
            results = await ptdata.search_legislation(
                query=input_data.description,
                limit=10,
            )
        except Exception as e:
            logger.warning(f"Failed to search legislation: {e}")
            results = []
        
        if not results:
            return TaxAnalysisOutput(
                decision="uncertain",
                confidence=0.20,
                legal_basis=[],
                explanation="Não foi possível encontrar base legal para esta operação.",
                risks=["Sem legislação encontrada"],
                assumptions=[],
                required_followup=["Verificar manualmente a legislação aplicável"],
                risk_level="high",
                legal_version_timestamp="2024-01-01T00:00:00Z",
            )
        
        # Update system prompt with memory context
        enhanced_system_prompt = LLM_SYSTEM_PROMPT.format(
            memory_context=memory_context
        )
        
        if self.use_iaedu and settings.iaedu_api_key:
            return await self._analyze_with_iaedu(input_data, results, enhanced_system_prompt)
        else:
            return await self._analyze_fallback(input_data, results)
    
    async def _analyze_with_iaedu(
        self,
        input_data: TaxAnalysisInput,
        legislation_results: list[dict],
    ) -> TaxAnalysisOutput:
        """Analyze using IAEDU API."""
        
        iaedu = get_iaedu_client()
        
        context = self._build_legal_context(legislation_results)
        user_prompt = self._build_user_prompt(input_data)
        
        full_prompt = f"""{LLM_SYSTEM_PROMPT}

Legislação relevante:
{context}

Operação a analisar:
{user_prompt}

Responda apenas com JSON válido, sem texto adicional.
"""
        
        logger.info("Sending request to IAEDU...")
        
        try:
            response = await iaedu.chat_complete(
                message=full_prompt,
            )
            
            parsed = self._parse_llm_response(response)
            if parsed:
                return parsed
                
        except Exception as e:
            logger.error(f"IAEDU request failed: {e}")
        
        return await self._analyze_fallback(input_data, legislation_results)
    
    async def _analyze_fallback(
        self,
        input_data: TaxAnalysisInput,
        legislation_results: list[dict],
    ) -> TaxAnalysisOutput:
        """Fallback analysis when LLM is unavailable."""
        
        legal_basis = []
        for result in legislation_results[:3]:
            legal_basis.append(LegalCitation(
                code=result.get("code", "CIVA"),
                article=result.get("article", ""),
                excerpt=result.get("excerpt", "")[:200],
            ))
        
        return TaxAnalysisOutput(
            decision="uncertain",
            confidence=0.40,
            legal_basis=legal_basis,
            explanation="Análise requer validação manual com base legal. LLM não disponível.",
            risks=["Verificar elegibilidade específica"],
            assumptions=[],
            required_followup=["Consultar legislação completa"],
            risk_level="medium",
            legal_version_timestamp="2024-01-01T00:00:00Z",
        )
    
    def _build_legal_context(self, results: list[dict]) -> str:
        """Build legal context from search results."""
        context_parts = []
        for i, result in enumerate(results[:5], 1):
            code = result.get("code", "CIVA")
            article = result.get("article", "")
            excerpt = result.get("excerpt", "")[:500]
            context_parts.append(f"{i}. {code} - {article}: {excerpt}")
        
        return "\n\n".join(context_parts) if context_parts else "Sem legislação encontrada."
    
    def _build_user_prompt(self, input_data: TaxAnalysisInput) -> str:
        """Build user prompt from input data."""
        return f"""Tipo de operação: {input_data.operation_type}
Descrição: {input_data.description}
Valor: €{input_data.amount:,.2f} {input_data.currency}
Entidade: {input_data.entity_type}
Contexto:
  - Projeto: {input_data.context.project_type}
  - Atividade: {input_data.context.activity_type}
  - Localização: {input_data.context.location}"""
    
    def _parse_llm_response(self, response: str) -> Optional[TaxAnalysisOutput]:
        """Parse LLM response into TaxAnalysisOutput."""
        
        response = response.strip()
        
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            logger.warning("No JSON found in LLM response")
            return None
        
        try:
            data = json.loads(json_match.group())
            
            legal_basis = []
            for lb in data.get("legal_basis", []):
                legal_basis.append(LegalCitation(
                    code=lb.get("code", "CIVA"),
                    article=lb.get("article", ""),
                    excerpt=lb.get("excerpt", ""),
                ))
            
            return TaxAnalysisOutput(
                decision=data.get("decision", "uncertain"),
                confidence=float(data.get("confidence", 0.5)),
                legal_basis=legal_basis,
                explanation=data.get("explanation", ""),
                risks=data.get("risks", []),
                assumptions=data.get("assumptions", []),
                required_followup=data.get("required_followup", []),
                risk_level=data.get("risk_level", "medium"),
                legal_version_timestamp=data.get("legal_version_timestamp", "2024-01-01T00:00:00Z"),
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return None


_llm_reasoning: Optional[LLMReasoning] = None


def get_llm_reasoning() -> LLMReasoning:
    global _llm_reasoning
    if _llm_reasoning is None:
        _llm_reasoning = LLMReasoning()
    return _llm_reasoning
