# UP Tax Intelligence Layer

A backend decision engine that transforms Portuguese tax law into structured, legally grounded decisions for university administrative workflows.

## What This Is NOT

- A chatbot
- A generic Q&A system
- A substitute for financial/legal advice
- A standalone source of truth

## What This Is

- **Decision Engine** — provides structured tax analysis based on Portuguese law
- **API-first** — designed for integration into institutional workflows
- **Legally grounded** — all decisions backed by actual legal articles
- **Auditable** — every decision logged with full context and legal basis

## Quick Start

```bash
# Install dependencies
make install

# Run the service
make run

# Run tests
make test
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   API       │────▶│  Reasoning  │────▶│  Rule Engine │
│   Layer     │     │   Layer     │     │              │
└─────────────┘     └─────────────┘     └──────────────┘
       │                   │                    │
       ▼                   ▼                    ▼
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  Decision   │◀────│   Data      │◀────│   Legal     │
│   Layer     │     │   Layer     │     │   Sources   │
└─────────────┘     └─────────────┘     └──────────────┘
```

## Core Principles

1. **No legal basis → no decision** — return "uncertain" if no law found
2. **Uncertainty > wrong answer** — never hallucinate
3. **Rule Engine > LLM** — deterministic rules take precedence
4. **Everything auditable** — log all decisions with timestamp and legal sources

## Documentation

- [Installation Guide](docs/INSTALL.md)
- [Functional Requirements](docs/requirements.md)
- [Non-Functional Requirements](docs/non-functional-requirements.md)
- [Personas](docs/personas.md)
- [Architecture](docs/architecture.md)
- [API Specification](docs/api-spec.md)
- [TODO](docs/TODO.md)

## License

MIT