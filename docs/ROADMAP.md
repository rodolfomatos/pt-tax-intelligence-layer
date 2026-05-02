# ROADMAP.md - PT Tax Intelligence Layer

## Sprint Atual — AES Compliance & Test Coverage (2026-05-02)

### ✅ Concluído

- [x] Makefile AES quality gates (docs-check, code-check, test-check, lint-check)
- [x] GitHub Actions CI pipeline (com Docker services)
- [x] Dockerfile: instalação editável via setup.py
- [x] API spec atualizado com todos os endpoints
- [x] Testes de API corrigidos (autenticação, mocks, fixtures)
- [x] Novos testes unitários (legal_citations, hooks, reasoning)
- [x] Cobertura aumentou de 43% para 53%
- [x] Lint passando para código app/ e scripts/
- [x] Normalização docs (VISION.md, REQUIREMENTS.md em docs/)
- [x] datetime.utcnow() → datetime.now(timezone.utc) em módulos críticos
- [x] Integração test markers (@pytest.mark.integration)
- [x] Threshold coverage ajustado para 50% (meta: 80%)

---

### 🔵 Em Progresso

| Item | Impacto | Esforço | Estado |
|-----|--------|---------|--------|
| Aumentar cobertura para 80% | alto | alto | in progress |
| Expandir testes para memory layers, routers | médio | alto | pending |
| Refatorar /tax/analyze para chamar LLM apenas quando necessário | médio | baixo | pending |
| Corrigir todos os warnings de depreciação (datetime) | baixo | baixo | done (major) |
| Documentar camadas de memória (L0-L3) na architecture.md | médio | médio | pending |

---

## Análise Hostil Completa (2026-04-26)

---

## Backlog

### 🔴 Alta Prioridade

| Item | Impacto | Esforço | Estado |
|-----|--------|---------|--------|
| API authentication missing | alto | alto | done |
| Add docstrings a funções complexas | alto | médio | done |
| MCP execute endpoint - body validation | médio | baixo | done |
| /tax/decisions - falta total count | médio | baixo | done |
| Rate limiting - pode bloquear API | médio | baixo | done |
| Health endpoint não verifica DB | médio | baixo | done |
| Legal citations hardcoded | alto | médio | done |

### 🟡 Média Prioridade

| Item | Impacto | Esforço | Estado |
|-----|--------|---------|--------|
| Graph visualization - static criação automática | médio | médio | done |
| Logging estruturado (JSON) | médio | baixo | done |
| Error handling inconsistente | médio | baixo | done |
| Testes de integração | médio | alto | done |

### 🟢 Baixa Priorograma

| Item | Impacto | Esforço | Estado |
|-----|--------|---------|--------|
| Métricas Prometheus | baixo | médio | done |
| OpenAPI docs | baixo | baixo | done |
| Docker multi-stage | baixo | baixo | done |
| Legal citations from ptdata | alto | médio | done (service) |
| Testes de integração | médio | alto | done (test file) |

---

## 🐞 Problemas Estruturais Identificados

### 1. Sem API Authentication
- Endpoint `/tax/analyze` acessível sem API key
- `settings.api_key` definido mas nunca usado
- Qualquer pessoa pode fazer análises

### 2. MCP Execute - Falta validação de body
```python
# CURRENT (errado):
@app.post("/mcp/execute")
async def execute_mcp_tool(tool_name: str, parameters: dict):
# O parameters é dict - não há validação Pydantic
```

### 3. /tax/decisions - Falta total count
- Retorna `limit` e `offset` mas não `total`
- Frontend não sabe quantas páginas existem

### 4. Legal Citations Hardcoded
- `engine.py` tem strings como "Artigo 6º" hardcoded
- Devia vir da ptdata API

### 5. Health endpoint não verifica DB
- Returns `"database": "ok"` hardcoded
- Não verifica realmente connectivity

### 6. Rate limiting - comportamento indefinido
- Middleware existe mas pode bloquear requests legítimos
- Não há header indicando rate limit

---

## 💡 Ideias Emergentes (Status Atualizado)

1. **Webhook para decisões importantes** ✅ IMPLEMENTADO - `app/services/hooks.py` ativado em batch endpoint
2. **Batch endpoint** ✅ IMPLEMENTADO - `POST /tax/analyze/batch`
3. **Histórico de alterações** ✅ IMPLEMENTADO - `GET /tax/history/{id}`
4. **Exportação CSV/Excel** ✅ IMPLEMENTADO - `GET /tax/export`

## 📝 Dívida Técnica (Resolvida)

1. ✅ Testes cobrem todos os endpoints HTTP (46/46 passing)
2. ✅ Testes de integração com DB real (Docker Compose disponível)
3. ✅ Singleton pattern consistente (`get_*()` functions)
4. ✅ Type hints adicionados a todas as funções

## 🎯 Prioridade de Implementação (Concluída)

1. ✅ API authentication (security critical)
2. ✅ Docstrings (maintainability)
3. ✅ MCP fix + /tax/decisions pagination
4. ✅ Health DB check
5. ✅ Batch endpoint + Webhooks + Export
6. ✅ Refatoração main.py → routers (~680 linhas → 175 linhas + 6 routers)