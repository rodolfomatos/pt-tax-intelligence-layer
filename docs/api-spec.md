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