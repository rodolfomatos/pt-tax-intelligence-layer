# SYSTEM DESIGN PROMPT — UPORTO TAX INTELLIGENCE LAYER

## OBJECTIVE

Design and implement a backend service called:

"PT Tax Intelligence Layer"

This is NOT a chatbot.
This is a decision engine that provides structured, legally grounded tax analysis using Portuguese tax law via API (ptdata MCP).

The system must be production-oriented, API-first, and integration-ready.

---

## CORE REQUIREMENTS

### 1. INPUT SCHEMA (MANDATORY)

All analysis must be based on structured input:

{
  "operation_type": "expense | invoice | asset | contract",
  "description": "string",
  "amount": number,
  "currency": "EUR",
  "entity_type": "university | researcher | department | project",
  "context": {
    "project_type": "FCT | Horizon | internal | other",
    "activity_type": "taxable | exempt | mixed",
    "location": "PT | EU | non-EU"
  },
  "metadata": {}
}

---

### 2. OUTPUT SCHEMA (MANDATORY)

All responses must be structured:

{
  "decision": "deductible | non_deductible | partially_deductible | uncertain",
  "confidence": 0.0-1.0,
  "legal_basis": [
    {
      "code": "CIVA | CIRC | CIRS | etc",
      "article": "string",
      "excerpt": "string"
    }
  ],
  "explanation": "clear structured explanation",
  "risks": ["list of risks"],
  "assumptions": ["list of assumptions made"],
  "required_followup": ["questions if uncertain"]
}

---

### 3. LEGAL GROUNDING (CRITICAL)

- All decisions MUST be backed by legal articles retrieved via:
  https://api.ptdata.org/mcp

- If no legal basis is found:
  → return "uncertain"
  → NEVER hallucinate

---

### 4. ARCHITECTURE

Design the system with these layers:

#### A. Data Layer
- MCP integration with ptdata API
- Local cache of legislation (Redis or DB)

#### B. Reasoning Layer
- LLM (OpenAI or equivalent)
- Prompting with strict grounding rules
- Citation validation

#### C. Rule Engine (IMPORTANT)
- Deterministic rules:
  - VAT deduction logic
  - project-based constraints
  - activity classification

#### D. API Layer

Expose endpoints:

POST /tax/analyze
POST /tax/validate
GET /tax/search
GET /tax/article/{code}/{article}

---

### 5. FAILURE MODES

System must handle:

- Missing data → ask follow-up
- Conflicting law → return "uncertain"
- API failure → fallback to cache

---

### 6. MCP INTEGRATION

Implement MCP client to:
- query legislation
- retrieve full articles
- support semantic search

---

### 7. SAFETY + LEGAL

All responses must include:

"This is a preliminary automated assessment. Validate with financial or legal services."

---

### 8. EXTENSIBILITY

System must support:
- integration with internal university systems
- future rule injection
- audit logs

---

### 9. OUTPUT FORMAT

Produce:

1. Full system architecture (diagram + explanation)
2. API specification (OpenAPI format)
3. Core reasoning prompt for LLM
4. Example requests/responses
5. Failure handling strategy
6. Deployment plan

---

## CONSTRAINTS

- No UI required
- No chatbot behavior
- No generic explanations
- Must be deterministic where possible
- Must explicitly show where uncertainty exists
- Rule Engine MUST take precedence over LLM outputs
- All decisions must include at least one legal reference OR return "uncertain"
- Include "risk_level" in output
- Include "legal_version_timestamp"
- Log all decisions for auditability
- Require minimum 2 sources for high-confidence decisions
- If conflicting articles → return "uncertain"
- Never produce definitive answers in ambiguous contexts

---

## GOAL

Deliver a production-ready backend service that transforms Portuguese tax law into actionable, structured decisions for institutional workflows.

