import logging
from typing import Optional
from app.models import TaxAnalysisInput, TaxAnalysisOutput, LegalCitation

logger = logging.getLogger(__name__)


class RuleEngine:
    """Deterministic rule engine for tax decisions."""
    
    def evaluate(
        self,
        input_data: TaxAnalysisInput,
    ) -> Optional[TaxAnalysisOutput]:
        """Evaluate input against deterministic rules."""
        
        # VAT deduction rules based on CIVA
        if input_data.operation_type in ("expense", "invoice"):
            result = self._check_vat_deduction(input_data)
            if result:
                return result
        
        # Asset classification rules
        if input_data.operation_type == "asset":
            result = self._check_asset_classification(input_data)
            if result:
                return result
        
        # Contract rules
        if input_data.operation_type == "contract":
            result = self._check_contract_rules(input_data)
            if result:
                return result
        
        return None
    
    def _check_vat_deduction(
        self,
        input_data: TaxAnalysisInput,
    ) -> Optional[TaxAnalysisOutput]:
        """Check VAT deduction eligibility (CIVA rules)."""
        
        desc_lower = input_data.description.lower()
        project = input_data.context.project_type
        activity = input_data.context.activity_type
        location = input_data.context.location
        
        # Non-deductible: exempt activities
        if activity == "exempt":
            return TaxAnalysisOutput(
                decision="non_deductible",
                confidence=0.95,
                legal_basis=[
                    LegalCitation(
                        code="CIVA",
                        article="Artigo 6º",
                        excerpt="Estão isentas as operações...",
                    )
                ],
                explanation="Atividades isentas não dão direito à dedução de IVA.",
                risks=[],
                assumptions=[f"Atividadeclassificada como {activity}"],
                required_followup=[],
                risk_level="low",
                legal_version_timestamp="2024-01-01T00:00:00Z",
            )
        
        # Non-deductible: non-EU for non-taxable entities
        if location == "non-EU" and input_data.entity_type in ("researcher", "department"):
            return TaxAnalysisOutput(
                decision="non_deductible",
                confidence=0.90,
                legal_basis=[
                    LegalCitation(
                        code="CIVA",
                        article="Artigo 2º",
                        excerpt="O imposto incide sobre as transmissões de bens...",
                    )
                ],
                explanation="Despesas fora da UE não são dedutíveis para entidades não empresariais.",
                risks=["Verificar caso a caso com serviço financeiro"],
                assumptions=[f"Localização: {location}, entidade: {input_data.entity_type}"],
                required_followup=["Confirmar natureza da despesa"],
                risk_level="medium",
                legal_version_timestamp="2024-01-01T00:00:00Z",
            )
        
        # Deductible: internal project, taxable activity, PT/EU
        if project == "internal" and activity == "taxable" and location in ("PT", "EU"):
            # Check for specific non-deductible items
            non_deductible = [
                "despesas pessoais",
                "representação",
                "viagens de prazer",
                "alojamento - pessoal",
            ]
            
            for item in non_deductible:
                if item in desc_lower:
                    return TaxAnalysisOutput(
                        decision="non_deductible",
                        confidence=0.90,
                        legal_basis=[
                            LegalCitation(
                                code="CIVA",
                                article="Artigo 20º",
                                excerpt="São dedutíveis as despesas...",
                            )
                        ],
                        explanation=f"Despesas de {item} não são dedutíveis.",
                        risks=[],
                        assumptions=[f"Descrição: {input_data.description}"],
                        required_followup=[],
                        risk_level="low",
                        legal_version_timestamp="2024-01-01T00:00:00Z",
                    )
            
            return TaxAnalysisOutput(
                decision="deductible",
                confidence=0.85,
                legal_basis=[
                    LegalCitation(
                        code="CIVA",
                        article="Artigo 20º",
                        excerpt="São dedutíveis as despesas...",
                    )
                ],
                explanation="Despesa elegível para dedução de IVA.",
                risks=[],
                assumptions=[f"Projeto: {project}, atividade: {activity}"],
                required_followup=[],
                risk_level="low",
                legal_version_timestamp="2024-01-01T00:00:00Z",
            )
        
        # FCT/Horizon projects
        if project in ("FCT", "Horizon"):
            return TaxAnalysisOutput(
                decision="deductible",
                confidence=0.80,
                legal_basis=[
                    LegalCitation(
                        code="CIVA",
                        article="Artigo 20º",
                        excerpt="São dedutíveis as despesas...",
                    ),
                    LegalCitation(
                        code="CIRC",
                        article="Artigo 23º",
                        excerpt="Os custos são dedutíveis...",
                    ),
                ],
                explanation=f"Projetos {project} são elegíveis para dedução fiscal.",
                risks=["Verificar elegibilidade específica do projeto"],
                assumptions=[f"Projeto: {project}"],
                required_followup=["Confirmar que projeto está ativo"],
                risk_level="low",
                legal_version_timestamp="2024-01-01T00:00:00Z",
            )
        
        return None
    
    def _check_asset_classification(
        self,
        input_data: TaxAnalysisInput,
    ) -> Optional[TaxAnalysisOutput]:
        """Check asset classification (amortization)."""
        
        amount = input_data.amount
        
        # Small assets (< €1000) - immediate deduction
        if amount < 1000:
            return TaxAnalysisOutput(
                decision="deductible",
                confidence=0.95,
                legal_basis=[
                    LegalCitation(
                        code="CIRC",
                        article="Artigo 39º",
                        excerpt="Os ativos fixos tangíveis são amortizáveis...",
                    )
                ],
                explanation="Ativo de valor inferior a €1000 pode ser deduzido imediatamente.",
                risks=[],
                assumptions=[],
                required_followup=[],
                risk_level="low",
                legal_version_timestamp="2024-01-01T00:00:00Z",
            )
        
        # Large assets - need amortization
        return TaxAnalysisOutput(
            decision="partially_deductible",
            confidence=0.85,
            legal_basis=[
                LegalCitation(
                    code="CIRC",
                    article="Artigo 39º",
                    excerpt="Os ativos fixos tangíveis são amortizáveis...",
                )
            ],
            explanation=f"Ativo de €{amount:,.2f} requer plano de amortização.",
            risks=["Verificar taxa de amortização aplicável"],
            assumptions=[f"Valor: €{amount:,.2f}"],
            required_followup=["Consultar serviço financeiro para amortização"],
            risk_level="medium",
            legal_version_timestamp="2024-01-01T00:00:00Z",
        )
    
    def _check_contract_rules(
        self,
        input_data: TaxAnalysisInput,
    ) -> Optional[TaxAnalysisOutput]:
        """Check contract-related rules."""
        
        return TaxAnalysisOutput(
            decision="uncertain",
            confidence=0.30,
            legal_basis=[],
            explanation="Análise de contratos requer análise jurídica específica.",
            risks=["Contratos podem ter implicações fiscais complexas"],
            assumptions=[],
            required_followup=["Consultar serviço jurídico"],
            risk_level="high",
            legal_version_timestamp="2024-01-01T00:00:00Z",
        )


_rule_engine: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = RuleEngine()
    return _rule_engine
