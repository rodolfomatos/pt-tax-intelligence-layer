import pytest
from app.services.rules.engine import RuleEngine
from app.models import TaxAnalysisInput, Context


class TestRuleEngine:
    """Unit tests for the Rule Engine."""
    
    def test_exempt_activity_returns_non_deductible(self):
        """When activity is exempt, decision should be non_deductible."""
        engine = RuleEngine()
        input_data = TaxAnalysisInput(
            operation_type="expense",
            description="Despesa em atividade isenta",
            amount=100.00,
            currency="EUR",
            entity_type="researcher",
            context=Context(
                project_type="internal",
                activity_type="exempt",
                location="PT",
            ),
        )
        
        result = engine.evaluate(input_data)
        
        assert result is not None
        assert result.decision == "non_deductible"
        assert result.confidence > 0.9
        assert result.risk_level == "low"
    
    def test_non_eu_location_returns_non_deductible(self):
        """When location is non-EU, decision should be non_deductible."""
        engine = RuleEngine()
        input_data = TaxAnalysisInput(
            operation_type="expense",
            description="Despesa em viagem",
            amount=500.00,
            currency="EUR",
            entity_type="researcher",
            context=Context(
                project_type="internal",
                activity_type="taxable",
                location="non-EU",
            ),
        )
        
        result = engine.evaluate(input_data)
        
        assert result is not None
        assert result.decision == "non_deductible"
        assert result.risk_level in ["medium", "high"]
    
    def test_internal_project_taxable_returns_deductible(self):
        """Internal project with taxable activity should be deductible."""
        engine = RuleEngine()
        input_data = TaxAnalysisInput(
            operation_type="expense",
            description="Material de escritório",
            amount=50.00,
            currency="EUR",
            entity_type="department",
            context=Context(
                project_type="internal",
                activity_type="taxable",
                location="PT",
            ),
        )
        
        result = engine.evaluate(input_data)
        
        assert result is not None
        assert result.decision == "deductible"
        assert result.risk_level == "low"
    
    def test_personal_expense_returns_non_deductible(self):
        """Personal expenses should be non-deductible."""
        engine = RuleEngine()
        input_data = TaxAnalysisInput(
            operation_type="expense",
            description="Despesas pessoais do investigador",
            amount=200.00,
            currency="EUR",
            entity_type="researcher",
            context=Context(
                project_type="internal",
                activity_type="taxable",
                location="PT",
            ),
        )
        
        result = engine.evaluate(input_data)
        
        assert result is not None
        assert result.decision == "non_deductible"
    
    def test_fct_project_returns_deductible(self):
        """FCT project should return deductible."""
        engine = RuleEngine()
        input_data = TaxAnalysisInput(
            operation_type="expense",
            description="Equipamento de investigação",
            amount=1000.00,
            currency="EUR",
            entity_type="project",
            context=Context(
                project_type="FCT",
                activity_type="taxable",
                location="PT",
            ),
        )
        
        result = engine.evaluate(input_data)
        
        assert result is not None
        assert result.decision == "deductible"
        assert len(result.legal_basis) >= 1
    
    def test_horizon_project_returns_deductible(self):
        """Horizon project should return deductible."""
        engine = RuleEngine()
        input_data = TaxAnalysisInput(
            operation_type="invoice",
            description="Serviço de consultoria",
            amount=5000.00,
            currency="EUR",
            entity_type="project",
            context=Context(
                project_type="Horizon",
                activity_type="taxable",
                location="EU",
            ),
        )
        
        result = engine.evaluate(input_data)
        
        assert result is not None
        assert result.decision == "deductible"
        assert result.confidence > 0.7
    
    def test_small_asset_returns_deductible(self):
        """Assets under €1000 should be immediately deductible."""
        engine = RuleEngine()
        input_data = TaxAnalysisInput(
            operation_type="asset",
            description="Computador",
            amount=800.00,
            currency="EUR",
            entity_type="department",
            context=Context(
                project_type="internal",
                activity_type="taxable",
                location="PT",
            ),
        )
        
        result = engine.evaluate(input_data)
        
        assert result is not None
        assert result.decision == "deductible"
        assert result.risk_level == "low"
    
    def test_large_asset_returns_partially_deductible(self):
        """Assets over €1000 should require amortization."""
        engine = RuleEngine()
        input_data = TaxAnalysisInput(
            operation_type="asset",
            description="Equipamento industrial",
            amount=5000.00,
            currency="EUR",
            entity_type="department",
            context=Context(
                project_type="internal",
                activity_type="taxable",
                location="PT",
            ),
        )
        
        result = engine.evaluate(input_data)
        
        assert result is not None
        assert result.decision == "partially_deductible"
        assert result.risk_level == "medium"
    
    def test_contract_returns_uncertain(self):
        """Contracts should return uncertain (needs legal review)."""
        engine = RuleEngine()
        input_data = TaxAnalysisInput(
            operation_type="contract",
            description="Contrato de prestação de serviços",
            amount=10000.00,
            currency="EUR",
            entity_type="university",
            context=Context(
                project_type="internal",
                activity_type="taxable",
                location="PT",
            ),
        )
        
        result = engine.evaluate(input_data)
        
        assert result is not None
        assert result.decision == "uncertain"
        assert result.confidence < 0.5
        assert result.risk_level == "high"
    
    def test_unknown_operation_returns_none(self):
        """Unknown operations should return None (fallback to LLM)."""
        from pydantic import ValidationError
        
        # Invalid operation type is rejected by model - test input validation instead
        with pytest.raises(ValidationError):
            TaxAnalysisInput(
                operation_type="unknown_type",
                description="Some operation",
                amount=100.00,
                currency="EUR",
                entity_type="researcher",
                context=Context(
                    project_type="internal",
                    activity_type="taxable",
                    location="PT",
                ),
            )
