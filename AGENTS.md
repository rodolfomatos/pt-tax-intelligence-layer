# UP Tax Intelligence Layer — Agent Guidance

## What This Repo Is

**Backend decision engine** — NOT a chatbot. Transforms Portuguese tax law into structured, legally grounded decisions for university administrative workflows.

## Core Principles

1. **No legal basis → no decision** — always return "uncertain" if no law found
2. **Uncertainty > wrong answer** — never hallucinate
3. **Rule Engine > LLM** — deterministic rules take precedence
4. **Everything auditable** — log all decisions with timestamp and legal sources

## Input Schema

```json
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
  }
}
```

## Output Schema (Mandatory)

```json
{
  "decision": "deductible | non_deductible | partially_deductible | uncertain",
  "confidence": "0.0-1.0",
  "legal_basis": [{"code": "CIVA|CIRC|...", "article": "...", "excerpt": "..."}],
  "explanation": "string",
  "risks": [],
  "assumptions": [],
  "required_followup": [],
  "risk_level": "low|medium|high",
  "legal_version_timestamp": "ISO8601"
}
```

## Key Constraints

- Minimum 2 legal sources for high-confidence decisions
- Conflicting articles → return "uncertain"
- Include disclaimer: "This is a preliminary automated assessment. Validate with financial or legal services."
- All decisions logged for auditability

## Endpoints

- `POST /tax/analyze` — main decision endpoint
- `POST /tax/validate` — validate existing decisions
- `GET /tax/decisions` — list past decisions
- `GET /tax/statistics` — decision statistics
- `GET /tax/search` — search legislation
- `GET /tax/article/{code}/{article}` — retrieve specific article
- `GET /health` — health check

## Tech Notes

- Uses ptdata MCP API for legal grounding
- Layered architecture: Data → Reasoning → Rule Engine → Decision → Integration
- LLM assists but doesn't make final decisions

## Documentation

Documentation is in `docs/`:
- `requirements.md` — Functional requirements
- `non-functional-requirements.md` — Performance, security, etc.
- `personas.md` — User personas
- `architecture.md` — System architecture
- `api-spec.md` — API specification
- `TODO.md` — Project tasks

## Auto-Generated Documentation

When code changes, run `make docs` to update docs from code:
- `scripts/generate_docs.py` extracts endpoints, models, and updates docs

Run `make docs` after:
- Adding/modifying endpoints
- Changing API models
- Updating architecture