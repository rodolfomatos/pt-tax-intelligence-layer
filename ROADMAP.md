# ROADMAP.md - UP Tax Intelligence Layer

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

## 💡 Ideias Emergentes

1. **Webhook para decisões importantes** - notificar quando risco alto
2. **Batch endpoint** - analisar várias despesas de uma vez
3. **Histórico de alterações** - versionar decisões
4. **Exportação CSV/Excel** - para relatórios

---

## 📝 Dívida Técnica

1. Testes cobrem lógica mas não endpoints HTTP
2. Sem testes de integração com DB real
3. Singleton pattern usado inconsistentemente
4. Algumas funções sem type hints

---

## 🎯 Prioridade de Implementação

1. API authentication (security critical)
2. Docstrings (maintainability)
3. MCP fix + /tax/decisions pagination
4. Health DB check