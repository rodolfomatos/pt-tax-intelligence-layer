# Arquitetura — UP Tax Intelligence Layer

## 1. Visão Geral

Arquitetura em camadas que separa responsabilidades e garante auditabilidade.

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer                                 │
│   POST /tax/analyze | /validate | GET /search | /article        │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                      Decision Layer                             │
│         Agregação | Scoring | Risk Assessment | Logging          │
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                                           ▼
┌───────────────────┐                     ┌───────────────────┐
│  Rule Engine      │                     │  Reasoning Layer  │
│  (Determinístico) │                     │  (LLM + Prompt)   │
└───────────────────┘                     └───────────────────┘
        │                                           │
        └─────────────────────┬─────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Data Layer                                 │
│          ptdata MCP | Cache | PostgreSQL | Redis                │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Camadas

### 2.1 API Layer (`/api`)

**Responsabilidade:** HTTP handling, validation, error mapping

**Componentes:**
- FastAPI application
- Request/response models (Pydantic)
- Input validation
- Error handlers

**Endpoints:**
- `POST /tax/analyze` — análise principal
- `POST /tax/validate` — validação
- `GET /tax/search` — pesquisa
- `GET /tax/article/{code}/{article}` — artigo
- `GET /health` — health check
- `GET /metrics` — Prometheus metrics

### 2.2 Decision Layer (`/services/decision`)

**Responsabilidade:** Agregação de resultados, scoring final

**Componentes:**
- `DecisionAggregator` — combina LLM + rule engine
- `ConfidenceCalculator` — calcula score
- `RiskAssessor` — avalia riscos
- `AuditLogger` — regista tudo

**Fluxo:**
1. Recebe resultados de Reasoning + Rule Engine
2. Se rule engine tem decisão → usa essa
3. Se não, usa decisão LLM com validação
4. Calcula confiança
5. Identifica riscos
6. Log para auditoria

### 2.3 Rule Engine (`/services/rules`)

**Responsabilidade:** Lógica determinística

**Componentes:**
- `VATRules` — dedução IVA (CIVA)
- `ProjectRules` — restrições projeto (FCT, Horizon)
- `ActivityRules` — classificação atividades

**Características:**
- Sem dependência de LLM
- Override sobre LLM
- Completamente testável

**Exemplo de regra:**
```python
# Se atividade is taxable E localização is PT → deductible
# Se atividade is exempt → non_deductible
```

### 2.4 Reasoning Layer (`/services/reasoning`)

**Responsabilidade:** Extração e estruturação com LLM

**Componentes:**
- `LLMClient` — interface para OpenAI/Ollama
- `GroundingValidator` — valida citações
- `ResponseParser` — extrai estrutura

**Prompt key points:**
- Only answer if legal basis found
- Cite specific articles
- Return "uncertain" if ambiguous
- Never hallucinate

### 2.5 Data Layer (`/data`)

**Responsabilidade:** Dados e persistência

**Componentes:**
- `ptdata_client` — MCP client para API legislação
- `LegislationCache` — cache Redis/DB
- `AuditRepository` — PostgreSQL para logs
- `SessionManager` — gestão de estado

## 3. Fluxo de Dados

```
1. Request → API Layer
       ↓
2. Validate input → Decision Layer
       ↓
3. Check cache → Data Layer (ptdata)
       ↓
4. Parallel:
   a) Rule Engine → deterministic result
   b) Reasoning Layer → LLM result
       ↓
5. Decision Layer:
   - If Rule Engine has result → use it
   - Else validate LLM result
   - Calculate confidence
   - Assess risks
       ↓
6. Log audit → Data Layer
       ↓
7. Response → API Layer
```

## 4. Modelos de Dados

### Input
```python
class TaxAnalysisInput(BaseModel):
    operation_type: Literal["expense", "invoice", "asset", "contract"]
    description: str
    amount: float
    currency: Literal["EUR"]
    entity_type: Literal["university", "researcher", "department", "project"]
    context: Context
    metadata: dict = {}
```

### Output
```python
class TaxAnalysisOutput(BaseModel):
    decision: Literal["deductible", "non_deductible", "partially_deductible", "uncertain"]
    confidence: float
    legal_basis: list[LegalCitation]
    explanation: str
    risks: list[str]
    assumptions: list[str]
    required_followup: list[str]
    risk_level: Literal["low", "medium", "high"]
    legal_version_timestamp: datetime
```

### Audit Log
```python
class AuditLog(BaseModel):
    id: UUID
    timestamp: datetime
    input: dict
    output: TaxAnalysisOutput
    processing_time_ms: int
    source: str  # "rule_engine" | "llm" | "hybrid"
```

## 5. Error Handling

| Error Type | Handling | Response |
|------------|----------|----------|
| Invalid input | Validate + 422 | Detalhe do erro |
| ptdata unavailable | Fallback cache |Warning + cache data |
| LLM failure | Use rule engine | Warning + fallback |
| Conflicting law | Return uncertain | 200 + uncertain |
| Timeout | Retry + fallback | 504 + retry after |

## 6. Configuração

Variáveis de ambiente:
```
PTDATA_API_URL=https://api.ptdata.org/mcp
PTDATA_API_KEY=***
OPENAI_API_KEY=***  # ou Ollama endpoint
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
LOG_LEVEL=INFO
CACHE_TTL_SECONDS=86400
```

## 7. Diretórios

```
up-tax-intelligence-layer/
├── api/              # FastAPI endpoints
├── services/
│   ├── decision/     # Agregação de decisões
│   ├── rules/        # Rule engine
│   └── reasoning/    # LLM reasoning
├── data/
│   ├── ptdata/       # MCP client
│   ├── cache/        # Cache implementation
│   └── repository/   # DB access
├── models/           # Pydantic models
├── core/             # Config, logging, etc.
├── tests/
└── scripts/
```

## 8. Dependências Externas

| Serviço | Purpose | Fallback |
|---------|---------|----------|
| ptdata MCP | Legislação | Cache local |
| OpenAI/Ollama | LLM reasoning | Rule engine only |
| PostgreSQL | Audit logs | - |
| Redis | Cache | DB fallback |