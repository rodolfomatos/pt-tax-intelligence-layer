# HOWTO — UP Tax Intelligence Layer

## 1. Introdução

Este documento explica como configurar, executar e usar o UP Tax Intelligence Layer.

---

## 2. Quick Start

### 2.1 Docker (Recomendado)

```bash
# 1. Clone e configure
git clone <repository-url>
cd up-tax-intelligence-layer
cp .env.example .env

# 2. Edite o .env com as suas chaves
# See section 3 below

# 3. Iniciar serviços
make docker-up

# 4. Aceder à API
# API:      http://localhost:8000
# Docs:     http://localhost:8000/docs
# Health:   http://localhost:8000/health

# 5. Parar serviços
make docker-down
```

### 2.2 Desenvolvimento Local

```bash
# 1. Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configure .env
cp .env.example .env

# 4. Executar
make run

# 5. Tests
make test
```

---

## 3. Configuração

### Variáveis de Ambiente

Copie `.env.example` para `.env` e configure:

```bash
# === Legisão (obrigatório) ===
PTDATA_API_KEY=your_ptdata_api_key
PTDATA_API_URL=https://api.ptdata.org/mcp

# === LLM (escolha uma opção) ===

# Opção A: IAEDU (GRÁTIS - universidades portuguesas)
USE_IAEDU=true
IAEDU_API_KEY=your_iaedu_api_key
IAEDU_ENDPOINT=https://api.iaedu.pt/agent-chat/api/v1/agent/cmamvd3n40000c801qeacoad2/stream
IAEDU_CHANNEL_ID=cmh0rfgmn0i64j801uuoletwy

# Opção B: OpenAI
# USE_IAEDU=false
# OPENAI_API_KEY=sk-...

# Opção C: Ollama (local)
# USE_IAEDU=false
# OLLAMA_BASE_URL=http://localhost:11434

# === Database ===
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tax_intelligence

# === Cache ===
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=86400

# === Rate Limiting ===
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# === Logging ===
LOG_LEVEL=INFO
```

### Selecionar o LLM

| Opção | Custo | Como Ativar |
|-------|-------|-------------|
| **IAEDU** | Grátis (UPorto) | `USE_IAEDU=true` + API key |
| **OpenAI** | Pago | `USE_IAEDU=false` + `OPENAI_API_KEY` |
| **Ollama** | Grátis (local) | `USE_IAEDU=false` + `OLLAMA_BASE_URL` |

---

## 4. Exemplos de Uso

### 4.1 Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
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

### 4.2 Analisar Despesa (endpoint principal)

```bash
curl -X POST http://localhost:8000/tax/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "operation_type": "expense",
    "description": "Alojamento em conferência internacional",
    "amount": 150.00,
    "currency": "EUR",
    "entity_type": "researcher",
    "context": {
      "project_type": "FCT",
      "activity_type": "taxable",
      "location": "PT"
    }
  }'
```

**Response:**
```json
{
  "decision": "deductible",
  "confidence": 0.80,
  "legal_basis": [
    {
      "code": "CIVA",
      "article": "Artigo 20º",
      "excerpt": "São dedutíveis as despesas..."
    },
    {
      "code": "CIRC",
      "article": "Artigo 23º",
      "excerpt": "Os custos são dedutíveis..."
    }
  ],
  "explanation": "Projetos FCT são elegíveis para dedução fiscal.\n\nEsta é uma avaliação automática preliminar. Valide com os serviços financeiros ou jurídicos.",
  "risks": ["Verificar elegibilidade específica do projeto"],
  "assumptions": ["Projeto: FCT"],
  "required_followup": ["Confirmar que projeto está ativo"],
  "risk_level": "low",
  "legal_version_timestamp": "2024-01-01T00:00:00Z"
}
```

### 4.3 Validar Decisão

```bash
curl -X POST http://localhost:8000/tax/validate \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "deductible",
    "confidence": 0.95,
    "legal_basis": [
      {"code": "CIVA", "article": "20º", "excerpt": "Test"}
    ],
    "explanation": "Test",
    "risks": [],
    "assumptions": [],
    "required_followup": [],
    "risk_level": "low",
    "legal_version_timestamp": "2024-01-01T00:00:00Z"
  }'
```

**Response:**
```json
{
  "valid": true,
  "consistency_check": "passed",
  "notes": [],
  "warnings": []
}
```

### 4.4 Pesquisar Legislação

```bash
curl "http://localhost:8000/tax/search?q=dedução+IVA&code=CIVA&limit=5"
```

**Response:**
```json
{
  "results": [
    {
      "code": "CIVA",
      "article": "20º",
      "title": "Deduções",
      "excerpt": "São dedutíveis as despesas...",
      "relevance": 0.95
    }
  ],
  "total": 1,
  "query": "dedução+IVA",
  "cached": false
}
```

### 4.5 Obter Artigo Específico

```bash
curl http://localhost:8000/tax/article/CIVA/20
```

**Response:**
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

### 4.6 Listar Decisões Passadas

```bash
curl "http://localhost:8000/tax/decisions?limit=10&offset=0"
```

**Response:**
```json
{
  "decisions": [
    {
      "id": "uuid...",
      "created_at": "2024-01-15T10:00:00",
      "operation_type": "expense",
      "description": "Alojamento em conferência",
      "amount": 150.0,
      "decision": "deductible",
      "confidence": 0.8,
      "risk_level": "low",
      "source": "rule_engine"
    }
  ],
  "limit": 10,
  "offset": 0
}
```

### 4.7 Obter Estatísticas

```bash
curl http://localhost:8000/tax/statistics
```

**Response:**
```json
{
  "total": 150,
  "by_decision": {
    "deductible": 100,
    "non_deductible": 30,
    "partially_deductible": 15,
    "uncertain": 5
  },
  "avg_confidence": 0.82
}
```

---

## 5. Testes

### Executar Testes

```bash
make test
```

### Ver Documentação

```bash
make docs
# Output em docs/stats.json
```

---

## 6. Troubleshooting

### 6.1 Base de Dados

**Erro:** `connection refused`

```bash
# Verificar se PostgreSQL está a correr
make docker-up
# ou
docker ps

# Se não estiver, iniciar
docker-compose up -d db
```

### 6.2 API ptdata Indisponível

**Erro:** `ptdata unavailable`

O sistema usa cache local como fallback. Verifique:
- Rede connectivity
- Chave API correta em `.env`

### 6.3 LLM Não Responde

**Erro:** `LLM not responding`

Verifique:
- Se `USE_IAEDU=true` com chave correta
- Ou `OPENAI_API_KEY` configurado
- Ou `OLLAMA_BASE_URL` a apontar para Ollama local

### 6.4 Rate Limiting

**Erro:** `429 Too Many Requests`

```
X-RateLimit-Limit-Per-Minute: 60
X-RateLimit-Remaining-Per-Minute: 0
```

Aguarde ou ajuste limits no `.env`:
```bash
RATE_LIMIT_PER_MINUTE=120
RATE_LIMIT_PER_HOUR=2000
```

### 6.5 Redis Cache

**Erro:** `Cache unavailable`

```bash
# Verificar Redis
docker-compose up -d cache

# Ou usar DB fallback (mais lento)
# Remova REDIS_URL do .env
```

---

## 7. Comandos Úteis

| Comando | Descrição |
|---------|-----------|
| `make docker-up` | Iniciar serviços |
| `make docker-down` | Parar serviços |
| `make docker-logs` | Ver logs |
| `make test` | Executar testes |
| `make shell` | Abrir shell no container |
| `make db` | Abrir psql |
| `make status` | Ver estado dos serviços |

---

## 8. Mais Informação

- [API Specification](api-spec.md)
- [Architecture](architecture.md)
- [Requirements](requirements.md)
- [Installation](INSTALL.md)