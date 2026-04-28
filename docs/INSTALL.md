# Installation Guide

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (recommended)
- Access to ptdata MCP API (for legal grounding)

## Local Development Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd pt-tax-intelligence-layer
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Or using Make:

```bash
make install
```

### 4. Configure environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:
- `PTDATA_API_KEY` — API key for ptdata MCP
- `OPENAI_API_KEY` — API key for LLM (or use Ollama)
- `DATABASE_URL` — PostgreSQL connection string

### 5. Run the service

```bash
make run
```

The API will be available at `http://localhost:8000`

## Docker Setup (Recommended)

### Build and run

```bash
make docker-build
make docker-up
```

### Stop services

```bash
make docker-down
```

## Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# Run tests
make test
```

## Troubleshooting

### Database connection issues

Ensure PostgreSQL is running and credentials are correct in `.env`.

### ptdata API unavailable

The system will fall back to cached data. Check network connectivity.

### LLM not responding

Verify `OPENAI_API_KEY` is set, or configure Ollama endpoint in `.env`.
