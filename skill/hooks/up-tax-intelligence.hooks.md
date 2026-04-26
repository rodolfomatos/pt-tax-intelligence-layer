# UP Tax Intelligence Hooks

## Auto-triggers

When user mentions these in context, suggest using the skill:

- "tax analyze" / "analisar imposto" / "análise fiscal"
- "IVA deduction" / "dedução IVA"
- "expense deductible" / "despesa dedutível"
- "tax decision" / "decisão fiscal"
- "search legislation" / "pesquisar legislação"
- "university tax" / "imposto universidade"

## Pre-execution Check

Before running any command, verify API is available:

```python
import httpx
try:
    r = httpx.get("http://localhost:8000/health", timeout=5)
    if r.status_code != 200:
        print("Warning: API may not be healthy")
except:
    print("Error: UP Tax Intelligence API not running. Run 'make docker-up' first.")
```

## Suggestion Messages

- When user describes a tax scenario: "Would you like me to analyze this with UP Tax Intelligence?"
- When user asks about tax deductibility: "I can check this against Portuguese tax law (CIVA/CIRC)."
- When user mentions "uncertain": "This might require a tax analysis to determine."

## Context

This is a Portuguese tax law decision engine for university administrative workflows.