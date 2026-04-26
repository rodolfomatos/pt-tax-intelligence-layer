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

## Features

### Core
- Rule Engine for deterministic tax decisions (CIVA, CIRC)
- LLM reasoning with legal grounding (IAEDU, OpenAI, Ollama)
- Decision validation and confidence scoring
- PostgreSQL audit logging

### Data & Caching
- Redis cache with TTL and manual invalidation
- Semantic search with ChromaDB
- ptdata API integration for Portuguese legislation
- Legal citation service with fallback

### Knowledge Graph
- GMIF classification (M1-M7 epistemic levels)
- Decision graph with contradictions detection
- Timeline tracking per entity
- Visualization (D3.js)

### Integration
- MCP tools for external queries
- Webhooks and event hooks
- Prometheus metrics (/metrics)
- Dashboard endpoints (/dashboard/summary, /dashboard/trends)

### Operations
- API key authentication
- Rate limiting with headers
- Database migrations (Alembic)
- Performance benchmarks (/internal/benchmark)
- Error handling with JSON responses

## Quick Start

### Docker (Recommended)

```bash
# Clone and configure
git clone https://github.com/rodolfomatos/up-tax-intelligence-layer.git
cd up-tax-intelligence-layer
cp .env.example .env

# Edit .env with your keys

# Start services
make docker-up

# Access API
# API:      http://localhost:8000
# Docs:     http://localhost:8000/docs
# Health:   http://localhost:8000/health
```

### Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
make install

# Run the service
make run

# Run tests
make test
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `PTDATA_API_KEY` | ptdata API key for legislation | Yes |
| `DATABASE_URL` | PostgreSQL connection | Yes |
| `REDIS_URL` | Redis connection | No |
| `API_KEY` | API key for authentication | No |
| `USE_IAEDU` | Use IAEDU LLM (free) | No |
| `OPENAI_API_KEY` | OpenAI API key | No |
| `OLLAMA_BASE_URL` | Ollama local URL | No |

## API Endpoints

### Core
| Endpoint | Description |
|----------|------------|
| `POST /tax/analyze` | Analyze tax operation |
| `POST /tax/validate` | Validate existing decision |
| `GET /tax/decisions` | List past decisions |
| `GET /tax/statistics` | Decision statistics |

### Data
| Endpoint | Description |
|----------|------------|
| `GET /tax/search` | Search legislation |
| `GET /tax/article/{code}/{article}` | Get legal article |

### Knowledge Graph
| Endpoint | Description |
|----------|------------|
| `GET /tax/graph/stats` | Graph statistics |
| `GET /tax/graph/gmif-summary` | GMIF classification |
| `GET /tax/graph/contradictions` | Detect contradictions |
| `GET /tax/graph/timeline/{entity}` | Entity timeline |
| `GET /graph/visualize` | D3.js visualization |

### MCP Tools
| Endpoint | Description |
|----------|------------|
| `GET /mcp/tools` | List tools |
| `POST /mcp/execute` | Execute tool |

### Dashboard
| Endpoint | Description |
|----------|------------|
| `GET /dashboard/summary` | Aggregated statistics |
| `GET /dashboard/trends` | Decisions over time |

### Operations
| Endpoint | Description |
|----------|------------|
| `GET /health` | Health check |
| `GET /metrics` | Prometheus metrics |
| `GET /internal/benchmark` | Performance benchmark |

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
- [HOWTO - Usage Guide](docs/HOWTO.md)
- [Functional Requirements](docs/requirements.md)
- [Non-Functional Requirements](docs/non-functional-requirements.md)
- [Personas](docs/personas.md)
- [Architecture](docs/architecture.md)
- [API Specification](docs/api-spec.md)
- [Memory Systems Analysis](docs/memory-systems-analysis.md)
- [ROADMAP](ROADMAP.md)
- [TODO](docs/TODO.md)

## Makefile Commands

```bash
make install        # Install dependencies
make run          # Run development server
make test         # Run tests
make lint         # Run linting
make format       # Format code

make docker-up     # Start Docker services
make docker-down  # Stop Docker services
make docker-logs # Show logs

make alembic-migrate    # Run migrations
make alembic-rollback  # Rollback migration

make git-status   # Git status
make git-push   # Git push
make docs       # Generate documentation
```

## Tech Stack

- **FastAPI** - API framework
- **PostgreSQL** - Database with SQLAlchemy async
- **Redis** - Cache
- **ChromaDB** - Semantic search
- **Prometheus** - Metrics
- **Alembic** - Migrations
- **Docker** - Containerization

## License

MIT