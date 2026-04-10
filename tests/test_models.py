import pytest
from pydantic import ValidationError
from app.models import (
    TaxAnalysisInput, TaxAnalysisOutput, TaxValidationInput,
    Context, LegalCitation, HealthResponse,
)


class TestTaxAnalysisInput:
    """Unit tests for TaxAnalysisInput model."""
    
    def test_valid_input(self):
        """Valid input should parse successfully."""
        input_data = TaxAnalysisInput(
            operation_type="expense",
            description="Test expense",
            amount=100.00,
            currency="EUR",
            entity_type="researcher",
            context=Context(
                project_type="FCT",
                activity_type="taxable",
                location="PT",
            ),
        )
        
        assert input_data.operation_type == "expense"
        assert input_data.amount == 100.00
    
    def test_invalid_amount(self):
        """Negative amount should fail validation."""
        with pytest.raises(ValidationError):
            TaxAnalysisInput(
                operation_type="expense",
                description="Test",
                amount=-10.00,
                currency="EUR",
                entity_type="researcher",
                context=Context(
                    project_type="FCT",
                    activity_type="taxable",
                    location="PT",
                ),
            )
    
    def test_invalid_operation_type(self):
        """Invalid operation type should fail validation."""
        with pytest.raises(ValidationError):
            TaxAnalysisInput(
                operation_type="invalid",
                description="Test",
                amount=100.00,
                currency="EUR",
                entity_type="researcher",
                context=Context(
                    project_type="FCT",
                    activity_type="taxable",
                    location="PT",
                ),
            )
    
    def test_invalid_currency(self):
        """Non-EUR currency should fail validation."""
        with pytest.raises(ValidationError):
            TaxAnalysisInput(
                operation_type="expense",
                description="Test",
                amount=100.00,
                currency="USD",
                entity_type="researcher",
                context=Context(
                    project_type="FCT",
                    activity_type="taxable",
                    location="PT",
                ),
            )
    
    def test_default_context(self):
        """Context should have defaults."""
        input_data = TaxAnalysisInput(
            operation_type="expense",
            description="Test",
            amount=100.00,
            currency="EUR",
            entity_type="researcher",
            context=Context(),
        )
        
        assert input_data.context.project_type == "internal"
        assert input_data.context.activity_type == "taxable"
        assert input_data.context.location == "PT"


class TestTaxAnalysisOutput:
    """Unit tests for TaxAnalysisOutput model."""
    
    def test_valid_output(self):
        """Valid output should parse."""
        output = TaxAnalysisOutput(
            decision="deductible",
            confidence=0.95,
            legal_basis=[
                LegalCitation(code="CIVA", article="20º", excerpt="Test")
            ],
            explanation="Test explanation",
            risk_level="low",
            legal_version_timestamp="2024-01-01T00:00:00Z",
        )
        
        assert output.decision == "deductible"
        assert output.confidence == 0.95
    
    def test_invalid_confidence(self):
        """Confidence > 1.0 should fail."""
        with pytest.raises(ValidationError):
            TaxAnalysisOutput(
                decision="deductible",
                confidence=1.5,
                legal_basis=[],
                explanation="Test",
                risk_level="low",
                legal_version_timestamp="2024-01-01T00:00:00Z",
            )
    
    def test_invalid_decision(self):
        """Invalid decision should fail."""
        with pytest.raises(ValidationError):
            TaxAnalysisOutput(
                decision="invalid",
                confidence=0.5,
                legal_basis=[],
                explanation="Test",
                risk_level="low",
                legal_version_timestamp="2024-01-01T00:00:00Z",
            )
    
    def test_default_fields(self):
        """Optional fields should have defaults."""
        output = TaxAnalysisOutput(
            decision="deductible",
            confidence=0.5,
            legal_basis=[],
            explanation="Test",
            risk_level="low",
            legal_version_timestamp="2024-01-01T00:00:00Z",
        )
        
        assert output.risks == []
        assert output.assumptions == []
        assert output.required_followup == []


class TestLegalCitation:
    """Unit tests for LegalCitation model."""
    
    def test_valid_citation(self):
        """Valid citation should parse."""
        citation = LegalCitation(
            code="CIVA",
            article="20º",
            excerpt="Test excerpt",
        )
        
        assert citation.code == "CIVA"
        assert citation.article == "20º"
    
    def test_empty_citation(self):
        """Citation can have empty fields."""
        citation = LegalCitation(
            code="",
            article="",
            excerpt="",
        )
        
        assert citation.code == ""


class TestContext:
    """Unit tests for Context model."""
    
    def test_valid_context(self):
        """Valid context should parse."""
        ctx = Context(
            project_type="FCT",
            activity_type="taxable",
            location="PT",
        )
        
        assert ctx.project_type == "FCT"
    
    def test_default_context(self):
        """Context should have defaults."""
        ctx = Context()
        
        assert ctx.project_type == "internal"
        assert ctx.activity_type == "taxable"
        assert ctx.location == "PT"
    
    def test_invalid_project_type(self):
        """Invalid project type should fail."""
        with pytest.raises(ValidationError):
            Context(project_type="invalid")
    
    def test_invalid_location(self):
        """Invalid location should fail."""
        with pytest.raises(ValidationError):
            Context(location="invalid")
