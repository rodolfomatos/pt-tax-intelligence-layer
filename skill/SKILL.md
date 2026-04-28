---
name: up-tax-intelligence
description: Analyze Portuguese tax operations with legal grounding for university administrative workflows. Use when analyzing expenses/invoices for tax deductibility, validating decisions, or searching legislation.
origin: UP Tax Intelligence Layer
triggers:
  - "/tax-analyze"
  - "/tax-validate"
  - "/tax-search"
  - "/tax-decisions"
  - "tax" (in context)
---

# UP Tax Intelligence Skill

## When to Use

- Analyzing expenses/invoices for tax deductibility
- Validating existing tax decisions
- Searching Portuguese tax legislation (CIVA, CIRC)
- Assessing risks for university projects (FCT, Horizon)
- Getting dashboard statistics

## Input Schema

```json
{
  "operation_type": "expense | invoice | asset | contract",
  "description": "string describing the operation",
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

## Output

Structured JSON with:
- `decision`: deductible | non_deductible | partially_deductible | uncertain
- `confidence`: 0.0-1.0
- `legal_basis`: [{code, article, excerpt}]
- `explanation`: string in Portuguese
- `risks`, `assumptions`, `required_followup`: arrays
- `risk_level`: low | medium | high
- `legal_version_timestamp`: ISO8601

## Requirements

- UP Tax Intelligence API must be running
- Default: http://localhost:8000
- Override with PT_TAX_API_URL environment variable

## Installation

```bash
# Install as Claude Code skill
git clone https://github.com/rodolfomatos/up-tax-intelligence-skill.git ~/.claude/skills/up-tax-intelligence
```

## Usage

### Via command shim
```bash
# Analyze tax operation
echo '{"operation_type":"expense","description":"Office supplies","amount":50,"currency":"EUR","entity_type":"department","context":{"project_type":"internal","activity_type":"taxable","location":"PT"}}' | tax-analyze

# Validate decision
echo '{"decision":"deductible","confidence":0.85,"legal_basis":[...],"explanation":"..."}' | tax-validate

# Search legislation
echo '{"q":"IVA deduction","code":"CIVA"}' | tax-search
```

### Via skill trigger
In Claude Code, just mention "tax analyze" or use the skill directly:
> Analyze this expense for conference lodging in Portugal

## Commands Available

- `tax-analyze` - Main analysis endpoint
- `tax-validate` - Validate decisions
- `tax-search` - Search legislation
- `tax-decisions` - List past decisions
- `dashboard-summary` - Get dashboard stats

## Non-Negotiable Rules

- Never hallucinate legal articles
- Always include disclaimer in output
- Return "uncertain" when no clear legal basis
- Minimum 2 legal sources for high confidence decisions

## Links

- [Full Documentation](https://github.com/rodolfomatos/pt-tax-intelligence-layer)
- [API Docs](http://localhost:8000/docs)
- [Docker Setup](https://github.com/rodolfomatos/pt-tax-intelligence-layer#quick-start)