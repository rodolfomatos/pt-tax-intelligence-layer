---
generated: 2026-04-10T11:57:21.820323
endpoints: null
models: [
  {
    "name": "Context",
    "file": "app/models/__init__.py"
  },
  {
    "name": "TaxAnalysisInput",
    "file": "app/models/__init__.py"
  },
  {
    "name": "LegalCitation",
    "file": "app/models/__init__.py"
  },
  {
    "name": "TaxAnalysisOutput",
    "file": "app/models/__init__.py"
  },
  {
    "name": "TaxValidationInput",
    "file": "app/models/__init__.py"
  },
  {
    "name": "TaxValidationOutput",
    "file": "app/models/__init__.py"
  },
  {
    "name": "HealthResponse",
    "file": "app/models/__init__.py"
  }
]
---

---
generated: 2026-04-10T11:56:32.983730
endpoints: []
models: []
---

# Especificação da API — PT Tax Intelligence Layer

## 1. Visão Geral

API REST para análise fiscal de operações da universidade.

**Base URL:** `http://localhost:8000`  
**Versão:** `v1`  
**Formato:** JSON

---

## 2. Autenticação

### API Key

```
Authorization: Bearer <api_key>
```

Todos os endpoints (exceto `/health`) requerem autenticação.

---

## 3. Endpoints

### 3.1 POST /tax/analyze

Analisa uma operação e retorna decisão fiscal.

**Request:**
```http
POST /tax/analyze
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "operation_type": "expense",
  "description": "Alojamento em conferência internacional",
  "amount": 150.00,
  "currency": "EUR",
  "entity_type": "researcher",
  "context": {
    "project_type": "FCT",
    "activity_type": "taxable",
    "location": "PT"
  },
  "metadata": {}
}
```

**Response (200):**
```json
{
  "decision": "deductible",
  "confidence": 0.95,
  "legal_basis": [
    {
      "code": "CIVA",
      "article": "Artigo 20º",
      "excerpt": "São dedutíveis as despesas..."

    }
  ],
  "explanation": "A despesa de alojamento...",
  "risks": [],
  "assumptions": [
    "Projeto FCT ativo",
    "Atividade taxable"
  ],
  "required_followup": [],
  "risk_level": "low",
  "legal_version_timestamp": "2024-01-15T00:00:00Z"
}
```

**Erros:**
- `400` — Input inválido
- `401` — API key inválida
- `422` — Erro de validação
- `500` — Erro interno
- `503` — Serviço indisponível (fallback ativo)

---

### 3.2 POST /tax/validate

Valida uma decisão existente.

**Request:**
```http
POST /tax/validate
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "decision": "deductible",
  "confidence": 0.95,
  "legal_basis": [...],
  "explanation": "...",
  "risks": [],
  "assumptions": [],
  "required_followup": [],
  "risk_level": "low",
  "legal_version_timestamp": "2024-01-15T00:00:00Z"
}
```

**Response (200):**
```json
{
  "valid": true,
  "consistency_check": "passed",
  "notes": [],
  "warnings": []
}
```

---

### 3.3 GET /tax/search

Pesquisa legislação por termo.

**Request:**
```http
GET /tax/search?q=dedução+IVA&code=CIVA&limit=10
Authorization: Bearer <api_key>
```

**Response (200):**
```json
{
  "results": [
    {
      "code": "CIVA",
      "article": "Artigo 20º",
      "title": "Deduções",
      "excerpt": "São dedutíveis...",
      "relevance": 0.95
    }
  ],
  "total": 1,
  "query": "dedução+IVA"
}
```

---

### 3.4 GET /tax/article/{code}/{article}

Recupera artigo específico.

**Request:**
```http
GET /tax/article/CIVA/20
Authorization: Bearer <api_key>
```

**Response (200):**
```json
{
  "code": "CIVA",
  "article": "20º",
  "title": "Deduções",
  "content": "Artigo completo...",
  "version": "2024-01-01",
  "last_updated": "2024-01-15T00:00:00Z"
}
```

**Erros:**
- `404` — Artigo não encontrado

---

### 3.5 GET /health

Health check (sem autenticação).

**Response (200):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "ptdata": "ok",
    "database": "ok",
    "cache": "ok"
  }
}
```

---

### 3.6 GET /metrics

Métricas Prometheus (sem autenticação).

**Response (200):**
```
# HELP tax_analysis_total Total tax analyses
# TYPE tax_analysis_total counter
tax_analysis_total 1234

# HELP tax_decision_duration_seconds Decision latency
# TYPE tax_decision_duration_seconds histogram
...
```

---

### 3.7 GET /tax/decisions

List past tax decisions with pagination and optional filters.

**Request:**
```http
GET /tax/decisions?limit=100&offset=0&decision_type=deductible&entity_type=researcher&start_date=2024-01-01&end_date=2024-12-31
Authorization: Bearer <api_key>
```

**Response (200):**
```json
{
  "decisions": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "created_at": "2024-01-15T10:30:00Z",
      "operation_type": "expense",
      "description": "Alojamento em conferência",
      "amount": 150.0,
      "decision": "deductible",
      "confidence": 0.95,
      "risk_level": "low",
      "source": "rule_engine"
    }
  ],
  "limit": 100,
  "offset": 0,
  "total": 150
}
```

**Query Parameters:**
- `limit` (1-500): Number of results (default: 100)
- `offset` (>=0): Pagination offset (default: 0)
- `decision_type`: Filter by decision (deductible, non_deductible, partially_deductible, uncertain)
- `entity_type`: Filter by entity (university, researcher, department, project)
- `start_date`: ISO8601 datetime
- `end_date`: ISO8601 datetime

---

### 3.8 GET /tax/statistics

Get aggregate decision statistics.

**Request:**
```http
GET /tax/statistics
Authorization: Bearer <api_key>
```

**Response (200):**
```json
{
  "total": 1234,
  "by_decision": {
    "deductible": 800,
    "non_deductible": 200,
    "partially_deductible": 100,
    "uncertain": 134
  },
  "avg_confidence": 0.87
}
```

---

### 3.9 GET /tax/history/{decision_id}

Get historical changes for a specific decision.

**Request:**
```http
GET /tax/history/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <api_key>
```

**Response (200):**
```json
{
  "decision_id": "123e4567-e89b-12d3-a456-426614174000",
  "original": {
    "created_at": "2024-01-15T10:30:00Z",
    "decision": "deductible",
    "confidence": 0.95,
    "source": "rule_engine"
  },
  "history": [],
  "related_actions": []
}
```

---

### 3.10 POST /tax/analyze/batch

Batch tax analysis for multiple items.

**Request:**
```http
POST /tax/analyze/batch
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "items": [
    {
      "operation_type": "expense",
      "description": "Alojamento em conferência",
      "amount": 150.00,
      "currency": "EUR",
      "entity_type": "researcher",
      "context": {
        "project_type": "FCT",
        "activity_type": "taxable",
        "location": "PT"
      }
    }
  ],
  "stop_on_error": false
}
```

**Response (200):**
```json
{
  "total": 1,
  "successful": 1,
  "failed": 0,
  "results": [ { ... } ],
  "errors": []
}
```

---

### 3.11 GET /tax/export

Export decisions to CSV or Excel.

**Request:**
```http
GET /tax/export?format=csv&decision_type=deductible&entity_type=researcher
Authorization: Bearer <api_key>
```

**Query Parameters:**
- `format`: `csv` (default) or `excel`
- `decision_type`: Optional filter
- `entity_type`: Optional filter
- `start_date`: Optional ISO8601
- `end_date`: Optional ISO8601

**Response:**
- `text/csv` or Excel file with decisions.

---

### 3.12 GET /dashboard/summary

Dashboard summary statistics.

**Request:**
```http
GET /dashboard/summary
Authorization: Bearer <api_key>
```

**Response (200):**
```json
{
  "total_decisions": 1234,
  "recent_activity": 45,
  "top_entity_type": "researcher",
  "risk_distribution": {
    "low": 1000,
    "medium": 200,
    "high": 34
  }
}
```

---

### 3.13 GET /dashboard/trends

Decision trends over time (by day/week).

**Request:**
```http
GET /dashboard/trends?period=weekly
Authorization: Bearer <api_key>
```

**Response (200):**
```json
{
  "period": "weekly",
  "data": [
    {
      "date": "2024-01-07",
      "total": 150,
      "by_decision": {
        "deductible": 100,
        "non_deductible": 30,
        "partially_deductible": 10,
        "uncertain": 10
      }
    }
  ]
}
```

---

### 3.14 GET /internal/benchmark

Internal benchmark endpoint (performance testing).

**Request:**
```http
GET /internal/benchmark?iterations=100
Authorization: Bearer <api_key>
```

**Response (200):**
```json
{
  "iterations": 100,
  "avg_latency_ms": 250,
  "p95_latency_ms": 400,
  "total_time_seconds": 25.0
}
```

---

### 3.15 MCP Endpoints

#### 3.15.1 POST /mcp/execute

Execute an MCP tool.

**Request:**
```http
POST /mcp/execute
Content-Type: application/json

{
  "tool_name": "search_legislation",
  "parameters": {"query": "IVA", "limit": 5}
}
```

**Response (200):**
```json
{
  "content": [
    {"type": "text", "text": "..."}
  ]
}
```

#### 3.15.2 GET /mcp/tools

List available MCP tools.

**Request:**
```http
GET /mcp/tools
```

**Response (200):**
```json
{
  "tools": [
    {
      "name": "search_legislation",
      "description": "Search legislation",
      "inputSchema": { ... }
    }
  ]
}
```

#### 3.15.3 GET /mcp/resources

List MCP resources.

#### 3.15.4 GET /mcp/templates

List MCP prompt templates.

---

### 3.16 Graph Endpoints

#### 3.16.1 GET /graph/stats

Get knowledge graph statistics.

**Request:**
```http
GET /graph/stats
Authorization: Bearer <api_key>
```

**Response (200):**
```json
{
  "total_nodes": 1234,
  "total_edges": 5678,
  "gmif_distribution": {
    "M1": 100,
    "M2": 200
  }
}
```

#### 3.16.2 GET /graph/gmif-summary

Get GMIF classification summary.

**Request:**
```http
GET /graph/gmif-summary
Authorization: Bearer <api_key>
```

**Response (200):**
```json
{
  "summary": {
    "M1": {"count": 100, "avg_confidence": 0.9},
    "M2": {"count": 200, "avg_confidence": 0.8}
  }
}
```

#### 3.16.3 GET /graph/visualization/{type}

Get graph visualization data (JSON for frontend).

---

## 4. Schemas

### Input: TaxAnalysisInput

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| operation_type | enum | sim | Tipo de operação |
| description | string | sim | Descrição da operação |
| amount | float | sim | Valor |
| currency | string | sim | "EUR" |
| entity_type | enum | sim | Tipo de entidade |
| context | object | sim | Contexto adicional |
| context.project_type | enum | sim | Tipo de projeto |
| context.activity_type | enum | sim | Tipo de atividade |
| context.location | enum | sim | Localização |
| metadata | object | não | Metadados adicionais |

### Output: TaxAnalysisOutput

| Campo | Tipo | Descrição |
|-------|------|-----------|
| decision | enum | Decisão: deductible, non_deductible, partially_deductible, uncertain |
| confidence | float | Confiança 0.0-1.0 |
| legal_basis | array | Artigos legais |
| explanation | string | Explicação estruturada |
| risks | array | Riscos identificados |
| assumptions | array | Suposições feitas |
| required_followup | array | Follow-up necessário |
| risk_level | enum | low, medium, high |
| legal_version_timestamp | string | ISO8601 timestamp |

---

## 5. Rate Limiting

- **Limite:** 1000 pedidos/hora por API key
- **Headers:**
  - `X-RateLimit-Limit`: 1000
  - `X-RateLimit-Remaining`: 999
  - `X-RateLimit-Reset`: 3600

---

## 6. Códigos de Erro

| Código | Descrição |
|--------|-----------|
| 400 | Bad Request - input inválido |
| 401 | Unauthorized - API key inválida |
| 403 | Forbidden - sem permissão |
| 404 | Not Found - recurso não existe |
| 422 | Unprocessable Entity - erro de validação |
| 429 | Too Many Requests - rate limit excedido |
| 500 | Internal Server Error |
| 503 | Service Unavailable - fallback ativo |

---

## 7. OpenAPI

Documentação completa disponível em:  
`GET /docs` (Swagger UI)  
`GET /openapi.json` (OpenAPI 3.0)