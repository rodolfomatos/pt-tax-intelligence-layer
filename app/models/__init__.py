from pydantic import BaseModel, Field
from typing import Literal


class Context(BaseModel):
    """Tax analysis context with project and activity details."""
    project_type: Literal["FCT", "Horizon", "internal", "other"] = "internal"
    activity_type: Literal["taxable", "exempt", "mixed"] = "taxable"
    location: Literal["PT", "EU", "non-EU"] = "PT"


class TaxAnalysisInput(BaseModel):
    """Input for tax analysis."""
    operation_type: Literal["expense", "invoice", "asset", "contract"]
    description: str
    amount: float = Field(gt=0)
    currency: Literal["EUR"] = "EUR"
    entity_type: Literal["university", "researcher", "department", "project"]
    context: Context
    metadata: dict = Field(default_factory=dict)


class LegalCitation(BaseModel):
    code: str
    article: str
    excerpt: str


class TaxAnalysisOutput(BaseModel):
    decision: Literal["deductible", "non_deductible", "partially_deductible", "uncertain"]
    confidence: float = Field(ge=0.0, le=1.0)
    legal_basis: list[LegalCitation]
    explanation: str
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    required_followup: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    legal_version_timestamp: str


class TaxValidationInput(BaseModel):
    decision: str
    confidence: float
    legal_basis: list[LegalCitation]
    explanation: str
    risks: list[str] = []
    assumptions: list[str] = []
    required_followup: list[str] = []
    risk_level: Literal["low", "medium", "high"]
    legal_version_timestamp: str


class TaxValidationOutput(BaseModel):
    valid: bool
    consistency_check: str
    notes: list[str] = []
    warnings: list[str] = []


class HealthResponse(BaseModel):
    status: str
    version: str
    dependencies: dict


class MCPExecuteInput(BaseModel):
    """Input for MCP tool execution."""
    tool_name: str = Field(..., description="Name of the MCP tool to execute")
    parameters: dict = Field(default_factory=dict, description="Tool parameters")
